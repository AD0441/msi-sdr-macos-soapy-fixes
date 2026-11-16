#include <SoapySDR/Device.hpp>
#include <SoapySDR/Formats.hpp>
#include <chrono>
#include <complex>
#include <iostream>
#include <string>
#include <vector>

static size_t receive(SoapySDR::Device *dev,SoapySDR::Stream *stream) {
    std::vector<std::complex<float>> data(32768);
    void *buffers[]={data.data()};
    size_t samples=0;
    auto start=std::chrono::steady_clock::now();
    while(std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<0.2) {
        int flags=0; long long time=0;
        int n=dev->readStream(stream,buffers,data.size(),flags,time,100000);
        if(n>0) samples+=n;
    }
    return samples;
}

int main(int argc,char **argv) {
    std::string mode=argc>1?argv[1]:"start";
    SoapySDR::Device *dev=nullptr;
    SoapySDR::Stream *stream=nullptr;
    try {
        dev=SoapySDR::Device::make("driver=soapyMiri");
        if(!dev) throw std::runtime_error("MSI not found");
        dev->setSampleRate(SOAPY_SDR_RX,0,2048000);
        dev->setBandwidth(SOAPY_SDR_RX,0,1536000);
        dev->setFrequency(SOAPY_SDR_RX,0,100000000);
        stream=dev->setupStream(SOAPY_SDR_RX,SOAPY_SDR_CF32);
        int first=dev->activateStream(stream);
        size_t samples=first==0 && mode=="stop"?receive(dev,stream):0;
        int stopped=dev->deactivateStream(stream);
        bool detected=mode=="stop"?(first==0 && samples>0 && stopped<0):(first<0);
        int restarted=dev->activateStream(stream);
        size_t recovered=restarted==0?receive(dev,stream):0;
        int final_stop=dev->deactivateStream(stream);
        dev->closeStream(stream); stream=nullptr;
        SoapySDR::Device::unmake(dev); dev=nullptr;
        std::cout<<"{\"mode\":\""<<mode<<"\",\"first_activation\":"<<first<<",\"first_stop\":"<<stopped
                 <<",\"failure_detected\":"<<(detected?"true":"false")<<",\"restart\":"<<restarted
                 <<",\"recovered_samples\":"<<recovered<<",\"final_stop\":"<<final_stop<<"}\n";
        return detected && restarted==0 && recovered>0 && final_stop==0?0:2;
    } catch(const std::exception &e) {
        std::cerr<<e.what()<<'\n';
        if(dev && stream) {try {dev->deactivateStream(stream);dev->closeStream(stream);}catch(...){} }
        if(dev) SoapySDR::Device::unmake(dev);
        return 1;
    }
}
