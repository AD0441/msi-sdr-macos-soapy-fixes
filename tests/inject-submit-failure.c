#include <libusb.h>
#include <stdlib.h>
#include <stdatomic.h>

/* Only used by the local regression test process. */
static _Atomic unsigned int submissions;
static int fail_one_submit(struct libusb_transfer *transfer) {
    const char *setting = getenv("MSI_FAIL_SUBMIT");
    unsigned int nth = setting ? (unsigned int)strtoul(setting, NULL, 10) : 30;
    if (atomic_fetch_add(&submissions, 1) + 1 == nth) return LIBUSB_ERROR_IO;
    return libusb_submit_transfer(transfer);
}

__attribute__((used)) static struct {
    const void *replacement;
    const void *original;
} interpose[] __attribute__((section("__DATA,__interpose"))) = {
    {(const void *)fail_one_submit, (const void *)libusb_submit_transfer}
};
