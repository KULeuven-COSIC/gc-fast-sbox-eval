/*
 * YaoGarbleMaster.h
 *
 */

#ifndef YAO_YAOGARBLEMASTER_H_
#define YAO_YAOGARBLEMASTER_H_

#include "GC/ThreadMaster.h"
#include "GC/Secret.h"
#include "YaoGarbleWire.h"
#include "Processor/OnlineOptions.h"
#include <vector>

class YaoGarbleMaster : public GC::ThreadMaster<GC::Secret<YaoGarbleWire>>
{
    typedef GC::ThreadMaster<GC::Secret<YaoGarbleWire>> super;

    std::vector<std::vector<Key>> delta;

    void gen_delta(PRNG &prng, std::size_t dim);

public:
    bool continuous;
    int threshold;


    YaoGarbleMaster(bool continuous, OnlineOptions& opts, int threshold = 1024, int n_threads = 0);

    GC::Thread<GC::Secret<YaoGarbleWire>>* new_thread(int i);

    Key get_delta();


    const std::vector<Key>& get_deltas(std::size_t dim);
};

#endif /* YAO_YAOGARBLEMASTER_H_ */
