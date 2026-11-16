#!/usr/bin/env python3
"""Hardware regression: one MSI receiver, exclusive access, dedicated test processes.

Requires the probes and macOS interposer built against the runtime under test.
Does not install software, modify applications or save I/Q.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--abi', choices=['0.8', '0.8-3'], default='0.8')
    parser.add_argument('--driver-probe', type=Path, required=True)
    parser.add_argument('--soapy-probe', type=Path, required=True)
    parser.add_argument('--injector', type=Path, required=True)
    parser.add_argument('--open-probe', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    env = os.environ.copy()
    # A caller's old test setting must not silently change a scenario.
    for key in list(env):
        if key.startswith(('MSI_FAIL_', 'MSI_FAKE_')) or key == 'MSI_RESET_REENUMERATE':
            del env[key]
    env.update(SOAPY_SDR_ROOT=str(runtime),
               SOAPY_SDR_PLUGIN_PATH=str(runtime / 'lib/SoapySDR' / ('modules' + args.abi)),
               DYLD_INSERT_LIBRARIES=str(args.injector.resolve()))
    start = {'MSI_FAIL_CONTROL_REQUEST': '0x43', 'MSI_FAIL_CONTROL_ERROR': '-7'}
    stop = {'MSI_FAIL_CONTROL_REQUEST': '0x45', 'MSI_FAIL_CONTROL_NTH': '2', 'MSI_FAIL_CONTROL_ERROR': '-7'}
    alt = {'MSI_FAIL_ALTERNATE': '-7'}
    both = dict(start, MSI_FAIL_CONTROL_REQUEST_2='0x45', MSI_FAIL_CONTROL_NTH_2='2', MSI_FAIL_CONTROL_ERROR_2='-4')
    cases = [
        ('driver-start', args.driver_probe, ['-7'], start),
        ('driver-stop', args.driver_probe, ['-7'], stop),
        ('driver-alternate', args.driver_probe, ['-7'], alt),
        ('driver-first-error', args.driver_probe, ['-7'], both),
        ('driver-pause', args.driver_probe, ['-7', 'pause'], stop),
        ('driver-resume', args.driver_probe, ['-7', 'resume'], dict(start, MSI_FAIL_CONTROL_NTH='2')),
        ('soapy-start', args.soapy_probe, ['start'], start),
        ('soapy-stop', args.soapy_probe, ['stop'], stop),
        ('soapy-alternate', args.soapy_probe, ['alternate'], alt),
        ('soapy-first-error', args.soapy_probe, ['start-stop'], both),
    ]
    if args.open_probe:
        cases += [
            ('reset-reopen', args.open_probe, ['reset'], {'MSI_RESET_REENUMERATE': '1'}),
            ('busy-no-reset', args.open_probe, ['busy', '-6'], {'MSI_FAIL_CLAIM': '1'}),
            ('advisory-driver-flag', args.open_probe, ['reset'], {'MSI_FAKE_KERNEL_ACTIVE': '1'}),
            ('adc-init-error', args.open_probe, ['init', '-7'],
             {'MSI_FAIL_CONTROL_REQUEST': '0x41', 'MSI_FAIL_CONTROL_NTH': '2', 'MSI_FAIL_CONTROL_ERROR': '-7'}),
        ]
    results = []
    for name, probe, command_args, fault in cases:
        case_env = env.copy()
        case_env.update(fault)
        p = subprocess.run([str(probe.resolve())] + command_args,
                           env=case_env, capture_output=True, text=True, timeout=15)
        row = {'case': name, 'exit': p.returncode,
               'output': p.stdout.strip(), 'log': p.stderr.strip()}
        results.append(row)
        args.output.write_text(json.dumps(results, indent=2) + '\n')
        if p.returncode or 'INJECT ' not in p.stderr or 'pending=0' not in p.stderr:
            raise RuntimeError(name + ' failed: ' + p.stderr[-2000:])
        if name == 'reset-reopen' and ('reopened at the same physical port' not in p.stderr or 'reset_calls=1' not in p.stderr):
            raise RuntimeError('Reset did not reopen the receiver without a second reset')
        if name == 'busy-no-reset' and 'resets_before=0' not in p.stderr:
            raise RuntimeError('Busy receiver was reset before ownership was established')
        print('PASS ' + name, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
