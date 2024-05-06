/*
 * YaoWire.h
 *
 */

#ifndef YAO_YAOWIRE_H_
#define YAO_YAOWIRE_H_

#include "BMR/Key.h"
#include "BMR/Register.h"

class YaoWire : public Phase
{
protected:
	Key key_;

public:
	template<class T>
	static void xors(GC::Processor<T>& processor, const vector<int>& args);
	template<class T>
	static void xors(GC::Processor<T>& processor, const vector<int>& args,
			size_t start, size_t end);
	template<class T>
	static void xorm(GC::Processor<T>& processor, const vector<int>& args);
	template<class T>
	static void xormn(GC::Processor<T>& processor, const vector<int>& args);

	void XOR(const YaoWire& left, const YaoWire& right)
	{
		key_ = left.key_ ^ right.key_;
	}

	template<class T>
	void other_input(T&, int) {}

	static int count_proj_args(const std::vector<int> &args, size_t begin) {
		int n = 0;
		for(auto it = std::begin(args)+begin; it != std::end(args); it += 3) {
			n += *it;
		}
		return n;
	}
};

#endif /* YAO_YAOWIRE_H_ */
