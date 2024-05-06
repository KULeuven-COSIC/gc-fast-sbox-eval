#ifndef YAO_YAOGPROJATE_H_
#define YAO_YAOGPROJATE_H_

#include "config.h"
#include "BMR/Key.h"
#include "YaoGarbleWire.h"
#include "YaoEvalWire.h"
#include <array>
#include "Tools/MMO.h"

class YaoProjGate
{
	std::size_t n;
	Key* garbled_table;

public:

	YaoProjGate(std::size_t n, Key *garbled_table): n(n), garbled_table(garbled_table) {}

	void garble(PRNG &prng, MMO &mmo, YaoGarbleWire &out, const YaoGarbleWire &in, const std::vector<int> &args, std::size_t offset, const std::vector<Key> &delta_in,  const std::vector<Key> &delta_out, long counter);

	void eval(MMO &mmo, YaoEvalWire &out, const YaoEvalWire &in, long counter) const;

	// returns the number of entries in the garbled table
	inline std::size_t garbled_table_size() {
		#ifdef YAO_PROJ_NO_GRR
			return (1 << n);
		#else
			return (1 << n) -1;
		#endif
	}


	static inline Key hash(const Key &x, MMO &mmo, long) { return mmo.hash(x); }

	// returns the number of bytes of the garbled table
	static inline std::size_t sizeof_table(std::size_t n) {
		#ifdef YAO_PROJ_NO_GRR
			return (1 << n) * sizeof(Key);
		#else
			return ((1 << n) - 1) * sizeof(Key);
		#endif
	 }
};

#endif /* YAO_YAOPROJGATE_H_ */
