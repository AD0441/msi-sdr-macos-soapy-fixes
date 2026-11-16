/* macOS process-local fault injection and pending-transfer lifetime checks.
 * Never install this library inside an application bundle.
 */
#include <libusb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

typedef void (LIBUSB_CALL *callback_t)(struct libusb_transfer *);
static struct { struct libusb_transfer *transfer; callback_t callback; int active; } slots[256];
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned matches[2], alternate_calls, submitted_slots, freed_slots;
static unsigned reset_calls, claim_calls, open_successes, close_calls;

static long setting(const char *name, long fallback) {
    const char *value=getenv(name);
    return value ? strtol(value,NULL,0) : fallback;
}

static int checked_open(libusb_device *device,libusb_device_handle **handle) {
    int result=libusb_open(device,handle);
    if(result==0) {
        pthread_mutex_lock(&lock);
        ++open_successes;
        pthread_mutex_unlock(&lock);
    }
    return result;
}

static void checked_close(libusb_device_handle *handle) {
    pthread_mutex_lock(&lock);
    ++close_calls;
    pthread_mutex_unlock(&lock);
    libusb_close(handle);
}

static int checked_reset(libusb_device_handle *handle) {
    pthread_mutex_lock(&lock);
    unsigned occurrence=++reset_calls;
    pthread_mutex_unlock(&lock);
    int result=libusb_reset_device(handle);
    if(getenv("MSI_RESET_REENUMERATE") && occurrence==1 && result==0) {
        fprintf(stderr,"INJECT reset requires rediscovery\n");
        return LIBUSB_ERROR_NOT_FOUND;
    }
    return result;
}

static int checked_claim(libusb_device_handle *handle,int interface) {
    pthread_mutex_lock(&lock);
    int fail=getenv("MSI_FAIL_CLAIM") && ++claim_calls==1;
    if(fail) fprintf(stderr,"INJECT claim busy resets_before=%u\n",reset_calls);
    pthread_mutex_unlock(&lock);
    return fail ? LIBUSB_ERROR_BUSY : libusb_claim_interface(handle,interface);
}

static int checked_kernel_active(libusb_device_handle *handle,int interface) {
    if(getenv("MSI_FAKE_KERNEL_ACTIVE")) {
        fprintf(stderr,"INJECT advisory driver-active flag\n");
        return 1;
    }
    return libusb_kernel_driver_active(handle,interface);
}

static int inject_control(libusb_device_handle *handle, uint8_t type, uint8_t request,
                          uint16_t value, uint16_t index, unsigned char *data,
                          uint16_t length, unsigned int timeout) {
    pthread_mutex_lock(&lock);
    const char *keys[2]={"MSI_FAIL_CONTROL_REQUEST","MSI_FAIL_CONTROL_REQUEST_2"};
    const char *nth[2]={"MSI_FAIL_CONTROL_NTH","MSI_FAIL_CONTROL_NTH_2"};
    const char *errors[2]={"MSI_FAIL_CONTROL_ERROR","MSI_FAIL_CONTROL_ERROR_2"};
    int fail=0, result=0;
    for(unsigned i=0;i<2;++i) {
        if(type==0x42 && getenv(keys[i]) && request==setting(keys[i],-1)) {
            if(++matches[i]==setting(nth[i],1)) {
                result=(int)setting(errors[i],LIBUSB_ERROR_IO);
                fail=1;
                fprintf(stderr,"INJECT control request=0x%02x occurrence=%u error=%d\n",request,matches[i],result);
                break;
            }
        }
    }
    pthread_mutex_unlock(&lock);
    return fail ? result : libusb_control_transfer(handle,type,request,value,index,data,length,timeout);
}

static int inject_alternate(libusb_device_handle *handle,int interface,int alternate) {
    pthread_mutex_lock(&lock);
    int fail=getenv("MSI_FAIL_ALTERNATE") && ++alternate_calls==1;
    int result=(int)setting("MSI_FAIL_ALTERNATE",LIBUSB_ERROR_IO);
    if(fail) fprintf(stderr,"INJECT alternate interface=%d alternate=%d error=%d\n",interface,alternate,result);
    pthread_mutex_unlock(&lock);
    return fail ? result : libusb_set_interface_alt_setting(handle,interface,alternate);
}

static void LIBUSB_CALL checked_callback(struct libusb_transfer *transfer) {
    callback_t callback=NULL;
    pthread_mutex_lock(&lock);
    for(unsigned i=0;i<256;++i) if(slots[i].transfer==transfer) {
        slots[i].active=0;
        callback=slots[i].callback;
        break;
    }
    pthread_mutex_unlock(&lock);
    if(!callback) abort();
    callback(transfer);
}

static int checked_submit(struct libusb_transfer *transfer) {
    pthread_mutex_lock(&lock);
    unsigned i,empty=256;
    for(i=0;i<256;++i) {
        if(slots[i].transfer==transfer) break;
        if(!slots[i].transfer && empty==256) empty=i;
    }
    if(i==256) {
        if(empty==256) abort();
        i=empty;
        slots[i].transfer=transfer;
        ++submitted_slots;
    }
    if(transfer->callback!=checked_callback) slots[i].callback=transfer->callback;
    slots[i].active=1;
    transfer->callback=checked_callback;
    pthread_mutex_unlock(&lock);
    int result=libusb_submit_transfer(transfer);
    if(result<0) {
        pthread_mutex_lock(&lock);
        slots[i].active=0;
        pthread_mutex_unlock(&lock);
    }
    return result;
}

static void checked_free(struct libusb_transfer *transfer) {
    pthread_mutex_lock(&lock);
    for(unsigned i=0;i<256;++i) if(slots[i].transfer==transfer) {
        if(slots[i].active) {
            fprintf(stderr,"UNSAFE: freeing a pending USB transfer\n");
            abort();
        }
        slots[i].transfer=NULL;
        ++freed_slots;
        break;
    }
    pthread_mutex_unlock(&lock);
    libusb_free_transfer(transfer);
}

__attribute__((destructor)) static void report(void) {
    unsigned pending=0;
    for(unsigned i=0;i<256;++i) pending+=slots[i].active;
    fprintf(stderr,"LIFETIME submitted_slots=%u freed_slots=%u pending=%u\n",submitted_slots,freed_slots,pending);
    fprintf(stderr,"HANDLES opened=%u closed=%u reset_calls=%u\n",open_successes,close_calls,reset_calls);
    if(pending || submitted_slots!=freed_slots || open_successes!=close_calls) abort();
}

#define INTERPOSE(replacement,original) \
    __attribute__((used)) static struct { const void *replacement_ptr; const void *original_ptr; } \
    interpose_##original __attribute__((section("__DATA,__interpose"))) = { (const void *)&replacement, (const void *)&original }
INTERPOSE(inject_control,libusb_control_transfer);
INTERPOSE(inject_alternate,libusb_set_interface_alt_setting);
INTERPOSE(checked_submit,libusb_submit_transfer);
INTERPOSE(checked_free,libusb_free_transfer);
INTERPOSE(checked_open,libusb_open);
INTERPOSE(checked_close,libusb_close);
INTERPOSE(checked_reset,libusb_reset_device);
INTERPOSE(checked_claim,libusb_claim_interface);
INTERPOSE(checked_kernel_active,libusb_kernel_driver_active);
