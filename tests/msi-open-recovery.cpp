#include <mirisdr.h>
#include <atomic>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>

static void samples(unsigned char *,uint32_t length,void *context) {
    static_cast<std::atomic<size_t> *>(context)->fetch_add(length/4);
}

int main(int argc,char **argv) {
    std::string mode=argc>1?argv[1]:"reset";
    if(mode!="reset" && argc<3) return 64;
    mirisdr_dev_t *device=nullptr;
    int first=mirisdr_open(&device,0);
    bool valid=mode=="reset"?first==0:(first==std::stoi(argv[2]) && device==nullptr);
    if(!valid) {if(device)mirisdr_close(device);return 2;}
    if(mode!="reset" && mirisdr_open(&device,0)!=0) return 3;
    char bulk[]="BULK";
    mirisdr_set_transfer(device,bulk);
    mirisdr_set_sample_rate(device,2048000);
    std::atomic<size_t> count{0};
    std::atomic<bool> done{false};
    int stream_result=1;
    std::thread reader([&]{stream_result=mirisdr_read_async(device,samples,&count,0,0);done=true;});
    auto start=std::chrono::steady_clock::now();
    while(!done && std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<0.3)
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    while(!done) {
        mirisdr_cancel_async(device);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    reader.join();
    mirisdr_close(device);
    std::cout<<"{\"mode\":\""<<mode<<"\",\"first_result\":"<<first<<",\"stream_result\":"<<stream_result<<",\"samples\":"<<count<<"}\n";
    return stream_result==0 && count>0?0:4;
}
