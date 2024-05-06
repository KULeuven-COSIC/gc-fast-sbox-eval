#include "YaoProjGate.h"

void YaoProjGate::garble(PRNG &prng, MMO &mmo, YaoGarbleWire &out, const YaoGarbleWire &in, const std::vector<int> &args, std::size_t offset, const std::vector<Key> &delta_in, const std::vector<Key> &delta_out, long counter) {
  assert(delta_in.size() == n);
  #ifdef YAO_PROJ_NO_GRR
    // no garbled row reduction
    out.randomize(prng);
    Key wout = out.full_key();
    for(std::size_t x=0; x < (1ULL << n); x++) {
      uint8_t y = args[offset + x/4] >> (8*(x % 4));
      auto win = Key::prod(x, delta_in);
      win ^= in.full_key();
      auto row = hash(win, mmo, counter);
      row ^= Key::prod(y, delta_out);
      row ^= wout;
      garbled_table[win.get_signal(n)] = row;
    }
  #else
    // we don't use a prng when using GRR since the output wire label is determined
    // by the hash function output
    // this satisfies -Werror=unused-parameter
    (void)prng;

    // the first garbled table entry is fixed to a constant
    std::size_t x0 = in.full_key().get_signal(n);
    uint8_t y = args[offset + x0/4] >> (8*(x0 % 4));
    auto win = Key::prod(x0, delta_in);
    win ^= in.full_key();
    auto wout = hash(win, mmo, counter);
    wout ^= Key::prod(y, delta_out);
    out.set_full_key(wout);

    for(std::size_t x=0; x < (1ULL << n); x++) {
      if (x == x0)
        continue;
      y = args[offset + x/4] >> (8*(x % 4));
      win = Key::prod(x, delta_in);
      win ^= in.full_key();
      auto row = hash(win, mmo, counter);
      row ^= Key::prod(y, delta_out);
      row ^= wout;
      garbled_table[win.get_signal(n) - 1] = row;
    }
  #endif
}

void YaoProjGate::eval(MMO &mmo, YaoEvalWire &out, const YaoEvalWire &in, long counter) const {
  auto &win = in.key();
  auto i = win.get_signal(n);
  auto h = hash(win, mmo, counter);
  #ifdef YAO_PROJ_NO_GRR
    out.set(garbled_table[i] ^ h);
  #else
    if(i == 0) {
      out.set(h);
    }else{
      out.set(garbled_table[i-1] ^ h);
    }
  #endif

}
