#include <SoapySDR/Device.hpp>
#include <SoapySDR/Formats.hpp>
#include <chrono>
#include <complex>
#include <iostream>
#include <vector>

int main(int argc, char **argv) {
    const double rate = argc > 1 ? std::stod(argv[1]) : 2048000.0;
    const int cycles = argc > 2 ? std::stoi(argv[2]) : 5;
    const double seconds = argc > 3 ? std::stod(argv[3]) : 1.0;
    try {
        for (int cycle = 0; cycle < cycles; ++cycle) {
            auto *dev = SoapySDR::Device::make("driver=soapyMiri");
            if (!dev) throw std::runtime_error("MSI not found");
            dev->setSampleRate(SOAPY_SDR_RX, 0, rate);
            dev->setBandwidth(SOAPY_SDR_RX, 0, rate < 5000000 ? 1536000 : 6000000);
            dev->setFrequency(SOAPY_SDR_RX, 0, 100000000);
            auto *stream = dev->setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32);
            dev->activateStream(stream);
            std::vector<std::complex<float>> samples(32768);
            void *buffers[] = {samples.data()};
            size_t total = 0, errors = 0;
            double energy = 0;
            auto start = std::chrono::steady_clock::now();
            while (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds) {
                int flags = 0;
                long long time = 0;
                int n = dev->readStream(stream, buffers, samples.size(), flags, time, 100000);
                if (n > 0) {
                    total += n;
                    for (int i = 0; i < n; ++i) energy += std::norm(samples[i]);
                } else ++errors;
            }
            dev->deactivateStream(stream);
            dev->closeStream(stream);
            SoapySDR::Device::unmake(dev);
            std::cout << "cycle=" << cycle + 1 << " rate=" << rate << " samples=" << total
                      << " errors=" << errors << " mean_power=" << (total ? energy/total : 0) << std::endl;
            if (!total) return 2;
        }
    } catch (const std::exception &e) {
        std::cerr << e.what() << std::endl;
        return 1;
    }
}
