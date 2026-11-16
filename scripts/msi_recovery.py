#!/usr/bin/env python3
"""Restore verified MSI bundles or rebuild the integration from locked owner inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'recovery/manifest.json'

def load_lock():
    return json.loads(LOCK.read_text())

def run(args, cwd=None):
    p = subprocess.run(list(map(str, args)), cwd=cwd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError('Command failed: ' + str(args[0]) + '\n' + p.stdout[-1000:] + p.stderr[-2500:])
    return p.stdout

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def checked_asset(lock, cache, key):
    record = lock['assets'][key]
    path = cache / record['filename']
    if not path.is_file() or digest(path) != record['sha256']:
        raise RuntimeError('Missing or damaged locked asset: ' + record['filename'])
    return path

def safe_member(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        raise ValueError('Unsafe archive member: ' + name)

def safe_link(name, target, hard=False):
    safe_member(name)
    if target.startswith('/') or '\\' in target:
        raise ValueError('Absolute archive link')
    resolved = posixpath.normpath(target if hard else posixpath.join(posixpath.dirname(name), target))
    if resolved == '..' or resolved.startswith('../'):
        raise ValueError('Archive link escapes destination')

def safe_layout(entries, destination):
    """Reject writes through archive links or pre-existing destination symlinks."""
    links = {str(PurePosixPath(name)) for name, link in entries if link}
    for name, _ in entries:
        path = PurePosixPath(name)
        for parent in [path] + list(path.parents):
            if parent != path and str(parent) in links:
                raise ValueError('Archive member is nested under a link: ' + name)
            if (destination / str(parent)).is_symlink():
                raise ValueError('Archive destination contains a symlink: ' + name)

def extract_tar(path, destination):
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        for member in members:
            safe_member(member.name)
            if member.issym():
                safe_link(member.name, member.linkname)
            elif member.islnk():
                raise ValueError('Hard links are not supported in recovery archives')
            elif not (member.isfile() or member.isdir()):
                raise ValueError('Unsupported archive member type')
        safe_layout([(m.name, m.issym()) for m in members], destination)
        archive.extractall(destination)

def extract_zip(path, destination):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        for member in members:
            safe_member(member.filename)
            if stat.S_ISLNK(member.external_attr >> 16):
                safe_link(member.filename, archive.read(member).decode())
        safe_layout([(m.filename, stat.S_ISLNK(m.external_attr >> 16)) for m in members], destination)
    run(['ditto', '-x', '-k', path, destination])

def doctor():
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise RuntimeError('This locked recipe requires an Apple Silicon Mac')
    if int(platform.mac_ver()[0].split('.')[0]) < 26:
        raise RuntimeError('The locked binaries require macOS 26 or later')
    for tool in ['git', 'clang', 'clang++', 'ditto', 'codesign', 'otool', 'install_name_tool']:
        if not shutil.which(tool):
            raise RuntimeError('Required tool unavailable: ' + tool)
    sdk_version = run(['xcrun', '--sdk', 'macosx', '--show-sdk-version']).strip()
    if int(sdk_version.split('.')[0]) < 26:
        raise RuntimeError('Install Apple Command Line Tools with a macOS 26+ SDK')
    print('Ready: Apple Silicon, macOS ' + platform.mac_ver()[0] + ', SDK ' + sdk_version, flush=True)

def fetch(lock, args):
    kinds = {'inputs': {'original-application', 'source-snapshots', 'frozen-build-sdk'},
             'ready': {'ready-application'}, 'previous': {'previous-application'},
             'all': {'original-application', 'source-snapshots', 'frozen-build-sdk', 'ready-application', 'previous-application'}}[args.scope]
    args.cache.mkdir(parents=True, exist_ok=True)
    for key, record in lock['assets'].items():
        if record['kind'] not in kinds:
            continue
        target = args.cache / record['filename']
        if target.exists():
            checked_asset(lock, args.cache, key)
            print('Verified cached ' + record['filename'], flush=True)
            continue
        with tempfile.TemporaryDirectory(prefix='msi-download-', dir=str(args.cache)) as folder:
            run(['gh', 'release', 'download', lock['backup_tag'], '--repo', lock['backup_repository'],
                 '--pattern', record['filename'], '--dir', folder])
            downloaded = Path(folder) / record['filename']
            if digest(downloaded) != record['sha256']:
                raise RuntimeError('Downloaded checksum mismatch: ' + record['filename'])
            downloaded.rename(target)
        print('Downloaded and verified ' + record['filename'], flush=True)

def restore(lock, args):
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError('Restore output must be empty; no existing applications are replaced')
    args.output.mkdir(parents=True, exist_ok=True)
    variants = [args.variant] if args.variant else list(lock['applications'])
    for variant in variants:
        key = ('previous-' if args.previous else 'ready-') + variant
        archive = checked_asset(lock, args.cache, key)
        extract_zip(archive, args.output)
        app = args.output / lock['applications'][variant]['name']
        run(['codesign', '--verify', '--deep', '--strict', app])
        print('Restored and signature verified: ' + str(app), flush=True)

def verify_sources(lock, work):
    for name, record in lock['projects'].items():
        for relative, expected in record.get('expected_sources', {}).items():
            file = work / 'sources' / name / relative
            if not file.is_file() or digest(file) != expected:
                raise RuntimeError('Patched source differs from tested code: ' + name + '/' + relative)

def dependencies(path):
    lines = run(['otool', '-L', path]).splitlines()[1:]
    own = {s.strip() for s in run(['otool', '-D', path]).splitlines()[1:] if s.strip()}
    return [line.strip().split(' (compatibility version')[0] for line in lines
            if line.strip().split(' (compatibility version')[0] not in own]

def rpath(path, value):
    if value not in re.findall(r'path (.*?) \(offset', run(['otool', '-l', path])):
        run(['install_name_tool', '-add_rpath', value, path])

def normalize_library(path):
    run(['install_name_tool', '-id', '@rpath/' + path.name, path])
    for dep in dependencies(path):
        if dep.startswith(('/System/', '/usr/lib/')):
            continue
        if dep.startswith('/'):
            run(['install_name_tool', '-change', dep, '@rpath/' + Path(dep).name, path])
    rpath(path, '@loader_path')
    run(['codesign', '--force', '--sign', '-', path])

def prepare(lock, cache, work):
    marker = work / 'prepared.json'
    if marker.exists():
        if json.loads(marker.read_text())['manifest_sha256'] != digest(LOCK):
            raise RuntimeError('Workspace was prepared against a different lock file')
        verify_sources(lock, work)
        return
    if work.exists() and any(work.iterdir()):
        raise RuntimeError('Build workspace must initially be empty')
    work.mkdir(parents=True, exist_ok=True)
    extract_tar(checked_asset(lock, cache, 'sources'), work)
    extract_tar(checked_asset(lock, cache, 'sdk'), work)
    for variant, app in lock['applications'].items():
        destination = work / 'originals' / variant
        destination.mkdir(parents=True)
        extract_zip(checked_asset(lock, cache, 'original-' + variant), destination)
        original = destination / app['original_name']
        if app['core_sha256'] and digest(original / 'Contents/Frameworks/libsdrpp_core.dylib') != app['core_sha256']:
            raise RuntimeError('Unexpected core ABI fingerprint: ' + variant)
    for name, record in lock['projects'].items():
        source = work / 'sources' / name
        run(['git', 'init', '-q', source])
        for patch in record['patches']:
            run(['git', 'apply', '--check', ROOT / 'patches' / patch], cwd=source)
            run(['git', 'apply', ROOT / 'patches' / patch], cwd=source)
        if name in ('brown', 'ce'):
            shutil.copy2(ROOT / 'packaging/rx_lifecycle.h', source / 'source_modules/soapy_source/src/rx_lifecycle.h')
    verify_sources(lock, work)
    for library in (work / 'sdk/lib').glob('*.dylib'):
        normalize_library(library)
    marker.write_text(json.dumps({'manifest_sha256': digest(LOCK)}, indent=2) + '\n')
    print('Prepared original inputs and verified all tested source fingerprints', flush=True)

def compile_command(args, log):
    args = list(args) + ['-MMD', '-MF', str(log.with_suffix('.d'))]
    log.with_suffix('.command.json').write_text(json.dumps(list(map(str, args)), indent=2) + '\n')
    p = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    log.write_text(p.stdout + p.stderr)
    if p.returncode:
        raise RuntimeError('Build failed; see ' + str(log) + '\n' + p.stderr[-2200:])

def build_components(lock, work):
    sdk = work / 'sdk'
    output = work / 'components'
    output.mkdir(exist_ok=True)
    common = ['-O2', '-arch', 'arm64', '-mmacosx-version-min=26.0', '-Wl,-headerpad_max_install_names']
    miri = work / 'sources/mirisdr'
    driver = output / 'libmirisdr.4.dylib'
    compile_command(['clang', '-std=c11'] + common + ['-dynamiclib', '-Dmirisdr_EXPORTS',
        '-compatibility_version', '4.0.0', '-current_version', '4.0.0', '-I' + str(miri / 'include'),
        '-I' + str(sdk / 'include/libusb-1.0'), miri / 'src/libmirisdr.c', sdk / 'lib/libusb-1.0.0.dylib',
        '-install_name', '@rpath/libmirisdr.4.dylib', '-Wl,-rpath,@loader_path', '-o', driver], output / 'driver.log')
    for abi in ['0.8', '0.8-3']:
        headers = sdk / ('include' if abi == '0.8' else 'soapy-0.8-3')
        source = work / 'sources/soapymiri'
        target = output / ('libsoapyMiriSupport-' + abi + '.so')
        compile_command(['clang++', '-std=c++11'] + common + ['-bundle', '-I' + str(headers),
            '-I' + str(miri / 'include'), source / 'Registration.cpp', source / 'Settings.cpp', source / 'Streaming.cpp',
            driver, sdk / ('lib/libSoapySDR.' + abi + '.dylib'), '-Wl,-rpath,@loader_path/../../../../../Frameworks',
            '-o', target], output / ('module-' + abi + '.log'))
    for variant in ['sdrpp', 'brown', 'ce']:
        source = work / 'sources' / variant
        original = work / 'originals' / variant / lock['applications'][variant]['original_name']
        fw = original / 'Contents/Frameworks'
        includes = [source / p for p in ['core/src', 'core/src/imgui', 'core/backends/glfw', 'core/backends/glfw/imgui', 'core/libcorrect/include']]
        args = ['clang++', '-std=c++17'] + common + ['-dynamiclib', '-DGL_SILENCE_DEPRECATION',
            '-I' + str(sdk / 'include')] + ['-I' + str(p) for p in includes]
        args += [source / 'source_modules/soapy_source/src/main.cpp', fw / 'libsdrpp_core.dylib', sdk / 'lib/libSoapySDR.0.8.dylib']
        if variant == 'sdrpp':
            args += ['-undefined', 'dynamic_lookup'] + [sdk / 'lib' / p for p in ['libglfw.3.dylib', 'libfftw3f.3.dylib', 'libvolk.3.3.dylib', 'libzstd.1.dylib']]
            args += ['-framework', 'OpenGL']
        else:
            args += [fw / 'libvolk.3.2.dylib']
        args += ['-install_name', '@rpath/soapy_source.dylib', '-Wl,-rpath,@loader_path/../Frameworks',
                 '-o', output / ('soapy-source-' + variant + '.dylib')]
        compile_command(args, output / ('plugin-' + variant + '.log'))
        print('Built source plugin ' + variant, flush=True)
    brown = work / 'originals/brown' / lock['applications']['brown']['original_name']
    compile_command(['clang++', '-std=c++17'] + common + [ROOT / 'packaging/brown-msi-entry.cpp',
        brown / 'Contents/Frameworks/libsdrpp_core.dylib', '-Wl,-rpath,@executable_path/../Frameworks',
        '-o', output / 'brown-entry'], output / 'brown-entry.log')
    compile_command(['clang', '-fobjc-arc'] + common + [ROOT / 'packaging/msi-launcher.m',
        '-framework', 'Foundation', '-o', output / 'msi-launcher'], output / 'launcher.log')

def macho(path):
    if path.is_symlink() or not path.is_file():
        return False
    with path.open('rb') as f:
        return f.read(4) in [b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca']

def package(lock, work, output):
    import plistlib
    components = work / 'components'
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for variant, spec in lock['applications'].items():
        app = output / spec['name']
        if app.exists():
            raise RuntimeError('Refusing to overwrite bundle: ' + str(app))
        original = work / 'originals' / variant / spec['original_name']
        run(['cp', '-cR', original, app])
        for item in app.rglob('*'):
            if not item.is_symlink():
                item.chmod(item.stat().st_mode | 0o200)
        run(['xattr', '-cr', app])
        contents = app / 'Contents'
        fw = contents / 'Frameworks'
        resources = contents / 'Resources'
        executable = contents / 'MacOS' / spec['executable']
        executable.rename(executable.with_name(spec['executable'] + '-original'))
        if variant == 'brown':
            shutil.copy2(components / 'brown-entry', executable.with_name(spec['executable'] + '-original'))
        shutil.copy2(components / 'msi-launcher', contents / 'MacOS/msi-launcher')
        info_path = contents / 'Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info.update(CFBundleExecutable='msi-launcher', CFBundleDisplayName=app.stem,
                    CFBundleIdentifier=spec['bundle_identifier'], MSIVariant=variant,
                    MSIOriginalExecutable=spec['executable'] + '-original', MSISoapyABI=spec['abi'],
                    MSIApplicationKind='sdrangel' if variant == 'sdrangel' else 'sdrpp',
                    MSIIntegrationVersion=lock['revision'], LSMinimumSystemVersion=lock['minimum_macos'])
        info_path.write_bytes(plistlib.dumps(info))
        for name in ['libusb-1.0.0.dylib', 'libSoapySDR.' + spec['abi'] + '.dylib']:
            shutil.copy2(work / 'sdk/lib' / name, fw / name)
        shutil.copy2(components / 'libmirisdr.4.dylib', fw / 'libmirisdr.4.dylib')
        module = resources / ('msi-runtime/lib/SoapySDR/modules' + spec['abi'] + '/libsoapyMiriSupport.so')
        module.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(components / ('libsoapyMiriSupport-' + spec['abi'] + '.so'), module)
        if variant != 'sdrangel':
            shutil.copy2(components / ('soapy-source-' + variant + '.dylib'), contents / 'Plugins/soapy_source.dylib')
            defaults = resources / 'msi-defaults'
            defaults.mkdir(exist_ok=True)
            for p in (ROOT / 'recovery/defaults').glob('*.json'):
                shutil.copy2(p, defaults / p.name)
        else:
            old = resources / 'lib/SoapySDR'
            if old.exists():
                for p in old.rglob('*Miri*'):
                    if p.is_file():
                        p.unlink()
        queue = [p for p in contents.rglob('*') if macho(p)]
        seen = set()
        optional = []
        inherited_missing = []
        while queue:
            binary = queue.pop()
            if binary in seen:
                continue
            seen.add(binary)
            for dep in dependencies(binary):
                if dep.startswith(('/System/', '/usr/lib/')):
                    continue
                if dep.startswith('@rpath/') and (fw / dep[len('@rpath/'):]).exists():
                    continue
                if dep.startswith('@loader_path/') and (binary.parent / dep[len('@loader_path/'):]).exists():
                    continue
                if dep.startswith('@executable_path/') and (contents / 'MacOS' / dep[len('@executable_path/'):]).exists():
                    continue
                target = fw / Path(dep).name
                if not target.exists():
                    source = next((p for p in [work / 'sdk/extra' / variant / target.name,
                                               work / 'sdk/lib' / target.name] if p.is_file()), None)
                    if source:
                        shutil.copy2(source, target)
                        run(['install_name_tool', '-id', '@rpath/' + target.name, target])
                        queue.append(target)
                    elif any(s in binary.name.lower() for s in ['sdrplay', 'qsqlmimer', 'qsqlodbc', 'qsqlpsql']) or binary.name == 'sdrangelbench':
                        disabled = resources / 'optional-plugins-unavailable'
                        disabled.mkdir(exist_ok=True)
                        optional.append(str(binary.relative_to(app)))
                        binary.rename(disabled / binary.name)
                        break
                    elif variant == 'sdrangel' and binary.name == 'libopencv_videoio.410.dylib' and dep == '@loader_path/libOrbbecSDK.1.9.dylib':
                        # This camera SDK is absent in the locked original and tested MSI bundle.
                        inherited_missing.append({'file': str(binary.relative_to(app)), 'dependency': dep})
                        continue
                    else:
                        raise RuntimeError('Unresolved dependency in ' + binary.name + ': ' + dep)
                run(['install_name_tool', '-change', dep, '@rpath/' + target.name, binary])
                rpath(binary, '@loader_path/' + os.path.relpath(fw, binary.parent))
        for p in [fw / 'libmirisdr.4.dylib', fw / 'libusb-1.0.0.dylib', fw / ('libSoapySDR.' + spec['abi'] + '.dylib')]:
            normalize_library(p)
        licenses = resources / 'msi-licenses'
        licenses.mkdir(exist_ok=True)
        for name, record in lock['projects'].items():
            for filename in ['COPYING', 'LICENSE', 'LICENSE.txt']:
                notice = work / 'sources' / name / filename
                if notice.is_file():
                    shutil.copy2(notice, licenses / (name + '-' + filename))
        shutil.copytree(work / 'sdk/licenses', licenses / 'frozen-sdk', dirs_exist_ok=True)
        for binary in sorted([p for p in contents.rglob('*') if macho(p)], key=lambda p: len(p.parts), reverse=True):
            run(['codesign', '--force', '--sign', '-', binary])
        run(['codesign', '--force', '--deep', '--sign', '-', app])
        metadata = {'version': lock['revision'], 'rebuilt_from_locked_inputs': True,
                    'manifest_sha256': digest(LOCK), 'variant': variant, 'soapy_abi': spec['abi'],
                    'driver_sha256': digest(fw / 'libmirisdr.4.dylib'), 'module_sha256': digest(module),
                    'optional_plugins_disabled': optional, 'inherited_optional_missing_dependencies': inherited_missing}
        (resources / 'msi-integration.json').write_text(json.dumps(metadata, indent=2) + '\n')
        run(['codesign', '--force', '--sign', '-', app])
        run(['codesign', '--verify', '--deep', '--strict', app])
        archive = output / (app.stem + '-rebuilt.zip')
        run(['ditto', '-c', '-k', '--keepParent', '--norsrc', '--noextattr', app, archive])
        records.append({'application': app.name, 'archive': archive.name, 'sha256': digest(archive), 'signature': 'valid'})
        print('Packaged and verified ' + app.name, flush=True)
    (output / 'rebuild-results.json').write_text(json.dumps(records, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    p = sub.add_parser('fetch')
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--scope', choices=['ready', 'previous', 'inputs', 'all'], default='ready')
    p = sub.add_parser('restore')
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--variant', choices=['sdrpp', 'brown', 'ce', 'sdrangel'])
    p.add_argument('--previous', action='store_true')
    p = sub.add_parser('build')
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for name in ['cache', 'work', 'output']:
        if hasattr(args, name):
            setattr(args, name, getattr(args, name).resolve())
    lock = load_lock()
    if args.command == 'doctor':
        doctor()
    elif args.command == 'fetch':
        fetch(lock, args)
    elif args.command == 'restore':
        restore(lock, args)
    else:
        doctor()
        prepare(lock, args.cache, args.work)
        build_components(lock, args.work)
        package(lock, args.work, args.output)

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error))
