#include <cstdio>
#include <cstdlib>
#include <exception>

// Exported by the original Brown core. The GUI core saves configuration and
// shuts down its modules/backend before returning. Its later static waterfall
// destructor calls glDeleteTextures after the OpenGL context is gone; this also
// crashes --help, which never creates a context. Avoid that second teardown.
int sdrpp_main(int argc, char **argv);

int main(int argc, char **argv) {
    int result = 1;
    try { result = sdrpp_main(argc, argv); }
    catch (const std::exception &error) {
        std::fprintf(stderr, "Brown MSI: %s\n", error.what());
    }
    std::fflush(nullptr);
    std::_Exit(result);
}
