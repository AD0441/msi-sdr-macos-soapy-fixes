#pragma once
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <exception>
#include <thread>
#include <SoapySDR/Errors.h>

namespace msi {
inline int validatedIndex(double index, std::size_t count) {
    return std::isfinite(index) && index >= 0 && index < static_cast<double>(count)
        && index <= 2147483647.0 && std::floor(index) == index ? static_cast<int>(index) : 0;
}
// Read must use a finite timeout. Only this thread reads; it never closes Device.
template<class Read, class Swap, class Report>
void receiveLoop(std::atomic_bool& running, int capacity, Read read, Swap swap, Report report) noexcept {
    try {
        while (running.load(std::memory_order_acquire)) {
            const int result = read();
            if (!running.load(std::memory_order_acquire)) break;
            if (result > 0 && result <= capacity) {
                if (!swap(result)) break;
                continue;
            }
            if (result == 0 || result == SOAPY_SDR_TIMEOUT || result == SOAPY_SDR_OVERFLOW) {
                // Some backends return immediately on recoverable errors.
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
                continue;
            }
            // STREAM_ERROR, disconnect, unsupported operation, corrupt data, etc.
            report("readStream terminal error", result);
            break;
        }
    } catch (const std::exception& e) {
        report(e.what(), SOAPY_SDR_STREAM_ERROR);
    } catch (...) {
        report("readStream unknown exception", SOAPY_SDR_STREAM_ERROR);
    }
    running.store(false, std::memory_order_release);
}

// Caller serializes start/stop. A completed-but-joinable worker still needs cleanup.
template<class Device, class Stream, class Wake, class Reset, class Report>
void closeSession(std::atomic_bool& running, std::thread& worker, Device*& dev,
                  Stream*& devStream, Wake wakeWriter, Reset resetWriter, Report report) {
    running.store(false, std::memory_order_release);
    wakeWriter();                     // Release a worker blocked in stream.swap().
    if (worker.joinable()) worker.join(); // No readStream can race with destruction.
    auto attempt = [&](auto action) {
        try { action(); }
        catch (const std::exception& e) { report(e.what()); }
        catch (...) { report("unknown cleanup exception"); }
    };
    if (dev && devStream) {
        attempt([&] { dev->deactivateStream(devStream); });
        attempt([&] { dev->closeStream(devStream); });
    }
    devStream = nullptr;
    if (dev) attempt([&] { Device::unmake(dev); });
    dev = nullptr;
    resetWriter();
}
}
