/*
 * YaoGarbleMaster.cpp
 *
 */

#include "YaoGarbleMaster.h"
#include "YaoGarbler.h"

#include "GC/Machine.hpp"
#include "GC/Program.hpp"
#include "GC/Processor.hpp"
#include "GC/Secret.hpp"
#include "GC/Thread.hpp"
#include "GC/ThreadMaster.hpp"
#include "Processor/Instruction.hpp"
#include "YaoWire.hpp"

YaoGarbleMaster::YaoGarbleMaster(bool continuous, OnlineOptions& opts, int threshold, int n_threads) :
        super(opts, n_threads), delta(), continuous(continuous), threshold(threshold)
{
    PRNG prng;
    prng.ReSeed();
    gen_delta(prng, 8);
}

GC::Thread<GC::Secret<YaoGarbleWire>>* YaoGarbleMaster::new_thread(int i)
{
    return new YaoGarbler(i, *this);
}

Key YaoGarbleMaster::get_delta() {
    return delta[0][0];
}

const std::vector<Key>& YaoGarbleMaster::get_deltas(std::size_t dim) {
  assert(dim <= 8);
  return delta[dim-1];
}

void YaoGarbleMaster::gen_delta(PRNG & prng, std::size_t dim) {
  assert(delta.size() == 0);
  delta.resize(dim);
  for(std::size_t d = 1; d<=dim; d++) {
    std::vector<Key> delta_dim(d);
    for(std::size_t i=0; i < d; i++) {
      Key r = prng.get_doubleword();
      r.set_signal(d, 0x1 << i);
      delta_dim[i] = r;
    }
    delta[d-1] = delta_dim;
  }
}
