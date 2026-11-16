#include <mirisdr.h>
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

static void samples(unsigned char *,uint32_t len,void *ctx) {
    static_cast<std::atomic<size_t> *>(ctx)->fetch_add(len/4);
}

static int cycle(mirisdr_dev_t *dev,std::atomic<size_t> &count,const std::string &action="") {
    std::atomic<bool> done{false};
    int result=1;
    std::thread reader([&]{result=mirisdr_read_async(dev,samples,&count,0,0);done=true;});
    auto start=std::chrono::steady_clock::now();
    while(!done && std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<0.3)
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    if(!done && !action.empty()) {
        int paused=mirisdr_stop_async(dev);
        if(paused==0 && action=="resume") mirisdr_start_async(dev);
    }
    while(!done) {
        mirisdr_cancel_async(dev);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    reader.join();
    return result;
}

int main(int argc,char **argv) {
    int expected=argc>1?std::stoi(argv[1]):-7;
    mirisdr_dev_t *dev=nullptr;
    if(mirisdr_open(&dev,0)) return 1;
    char bulk[]="BULK";
    mirisdr_set_transfer(dev,bulk);
    mirisdr_set_sample_rate(dev,2048000);
    std::atomic<size_t> first_samples{0},second_samples{0};
    int first=cycle(dev,first_samples,argc>2?argv[2]:"");
    int second=cycle(dev,second_samples);
    mirisdr_close(dev);
    std::cout<<"{\"expected\":"<<expected<<",\"first_error\":"<<first<<",\"first_samples\":"<<first_samples
             <<",\"second_result\":"<<second<<",\"recovered_samples\":"<<second_samples<<"}\n";
    return first==expected && second==0 && second_samples>0?0:2;
}
