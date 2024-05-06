/*
 * Key.cpp
 *
 */


#include <string.h>
#include "Key.h"

Key Key::prod(uint8_t x, const std::vector<Key> &delta) {
	Key k(0LL);
	for(std::size_t i=0; i < delta.size(); i++) {
		if(((x >> i) & 0x1) > 0) {
			k ^= delta[i];
		}
	}
	return k;
}

void Key::set_signal(std::size_t n, uint8_t signal) {
	assert(n <= 8);
	long long mask = ~0ul << n;
	r &= ~_mm_cvtsi64_si128(~mask);
	r ^= _mm_cvtsi64_si128(signal);
}

uint8_t Key::get_signal(std::size_t n) const {
	assert(n <= 8);
	return (uint8_t)(get<unsigned long>()) & ~(0xFF << n);
}

ostream& operator<<(ostream& o, const Key& key)
{
	return o << key.r;
}

ostream& operator<<(ostream& o, const __m128i& x) {
	o.fill('0');
	o << hex << noshowbase;
	for (int i = 0; i < 2; i++)
	{
		o.width(16);
		o << ((int64_t*)&x)[1-i];
	}
	o << dec;
	return o;
}
