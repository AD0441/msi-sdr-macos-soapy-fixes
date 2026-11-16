#include <SoapySDR/Device.hpp>
#include <SoapySDR/Formats.hpp>
#include <chrono>
#include <complex>
#include <cmath>
#include <iostream>
#include <limits>
#include <vector>

static size_t readFor(SoapySDR::Device *dev, SoapySDR::Stream *stream, double seconds) {
    std::vector<std::complex<float>> buffer(32768);
    void *buffers[] = {buffer.data()};
    size_t count = 0;
    auto start = std::chrono::steady_clock::now();
    while (std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count() < seconds) {
        int flags = 0; long long time = 0;
        int n = dev->readStream(stream, buffers, buffer.size(), flags, time, 100000);
        if (n > 0) count += n;
    }
    return count;
}

int main(int argc, char **argv) {
    const int cycles = argc > 1 ? std::stoi(argv[1]) : 30;
    auto *dev = SoapySDR::Device::make("driver=soapyMiri");
    dev->setSampleRate(SOAPY_SDR_RX, 0, 2048000);
    for (double requested : {0.0, 1536000.0, 10000000.0, 14000000.0, -1.0,
                             std::numeric_limits<double>::quiet_NaN()}) {
        dev->setBandwidth(SOAPY_SDR_RX, 0, requested);
        double actual = dev->getBandwidth(SOAPY_SDR_RX, 0);
        std::cout << "bandwidth=" << requested << " actual=" << actual << std::endl;
        if (actual > 8000000 || actual <= 0) return 1;
    }
    dev->setFrequency(SOAPY_SDR_RX, 0, 100000000);
    auto *stream = dev->setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32);
    for (int i=0;i<cycles;++i) {
        if (dev->activateStream(stream) != 0 || dev->deactivateStream(stream) != 0) return 4;
    }
    std::cout << "start_stop_cycles=" << cycles << std::endl;
    dev->activateStream(stream);
    size_t samples = readFor(dev, stream, 1);
    dev->deactivateStream(stream);
    dev->activateStream(stream);
    samples = readFor(dev, stream, 1);
    std::cout << "restart_samples=" << samples << std::endl;
    if (!samples) return 2;
    for (double rate : {6000000.0, 2048000.0, 6000000.0, 2048000.0}) {
        dev->setSampleRate(SOAPY_SDR_RX, 0, rate);
        samples = readFor(dev, stream, .5);
        std::cout << "live_rate=" << rate << " samples=" << samples << std::endl;
        if (!samples) return 3;
    }
    // Destruction of an active device must join its receive thread safely.
    SoapySDR::Device::unmake(dev);
    std::cout << "active_destruction=ok" << std::endl;
}
