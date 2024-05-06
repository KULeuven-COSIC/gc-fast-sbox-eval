/*
 * ThreadMaster.cpp
 *
 */

#ifndef GC_THREADMASTER_HPP_
#define GC_THREADMASTER_HPP_

#include "ThreadMaster.h"
#include "Program.h"

#include "instructions.h"

#include "Machine.hpp"

namespace GC
{

template<class T>
ThreadMaster<T>* ThreadMaster<T>::singleton = 0;

template<class T>
ThreadMaster<T>& ThreadMaster<T>::s()
{
    if (singleton)
        return *singleton;
    else
        throw no_singleton("no singleton, maybe threads not supported");
}

template<class T>
ThreadMaster<T>::ThreadMaster(OnlineOptions& opts, int n_threads) :
        P(0), opts(opts), n_threads(n_threads)
{
    if (singleton)
        throw runtime_error("there can only be one");
    singleton = this;
}

template<class T>
void ThreadMaster<T>::run_tape(int thread_number, int tape_number, int arg)
{
    threads.at(thread_number)->tape_schedule.push({tape_number, arg});
}

template<class T>
void ThreadMaster<T>::join_tape(int thread_number)
{
    threads.at(thread_number)->join_tape();
}

template<class T>
Thread<T>* ThreadMaster<T>::new_thread(int i)
{
    return new Thread<T>(i, *this);
}

template<class T>
void ThreadMaster<T>::run()
{
    P = new PlainPlayer(N, 0xff << 24);

    machine.load_schedule(progname);

    if (T::needs_ot)
        for (int i = 0; i < machine.nthreads; i++)
            machine.ot_setups.push_back({*P, true});

    for (int i = 0; i < machine.nthreads; i++)
        threads.push_back(new_thread(i));
    for (auto thread : threads)
        thread->join_tape();

    Timer timer;
    timer.start();

    threads[0]->tape_schedule.push(0);

    for (auto thread : threads)
        thread->finish();

    // synchronize
    vector<octetStream> os(P->num_players());
    P->Broadcast_Receive(os);

    post_run();

    NamedCommStats stats = P->comm_stats;
    ExecutionStats exe_stats;
    size_t data_sent = P->comm_stats.total_data();
    for (auto thread : threads)
    {
        stats += thread->P->comm_stats;
        exe_stats += thread->processor.stats;
        data_sent += thread->data_sent();
        delete thread;
    }

    delete P;

    exe_stats.print();
    stats.print();

    cerr << "Time = " << timer.elapsed() << " seconds" << endl;
    cerr << "Data sent = " << data_sent * 1e-6 << " MB" << endl;
}

} /* namespace GC */

#endif
