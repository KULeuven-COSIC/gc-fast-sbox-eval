/*
 * YaoEvalWire.cpp
 *
 */

#include "config.h"
#include "YaoEvalWire.h"
#include "YaoGate.h"
#include "YaoEvaluator.h"
#include "YaoEvalInput.h"
#include "BMR/prf.h"
#include "BMR/common.h"
#include "GC/ArgTuples.h"

#include "GC/Processor.hpp"
#include "GC/Secret.hpp"
#include "GC/Thread.hpp"
#include "GC/ShareSecret.hpp"
#include "YaoCommon.hpp"
#include "YaoProjGate.h"

void YaoEvalWire::random()
{
	set(0);
}

void YaoEvalWire::public_input(bool value)
{
	(void)value;
	set(0);
}

template<bool repeat>
void YaoEvalWire::and_(GC::Processor<GC::Secret<YaoEvalWire> >& processor,
		const vector<int>& args)
{
	YaoEvaluator& party = YaoEvaluator::s();
	int total = processor.check_args(args, 4);
	int threshold = 1024;
	if (total < threshold)
	{
		// run in single thread
		and_singlethread<repeat>(processor, args, total);
		return;
	}

	processor.complexity += total;
	int i_thread = 0, start = 0;
	for (auto& x : party.get_splits(args, threshold, total, 0, 4))
	{
		auto i_gate = x[0];
		auto end = x[1];
		YaoGate* gate = (YaoGate*) party.gates.consume(
				i_gate * sizeof(YaoGate));
		party.jobs[i_thread++]->dispatch(YAO_AND_JOB, processor, args, start,
				end, i_gate, gate, party.get_gate_id(), repeat);
		party.counter += i_gate;
		start = end;
	}
	party.wait(i_thread);
}

template<bool repeat>
void YaoEvalWire::and_singlethread(GC::Processor<GC::Secret<YaoEvalWire> >& processor,
		const vector<int>& args, int total_ands)
{
	if (total_ands < 10)
		return processor.and_(args, repeat);
	processor.complexity += total_ands;
	size_t n_args = args.size();
	YaoEvaluator& party = YaoEvaluator::s();
	YaoGate* gate = (YaoGate*) party.gates.consume(total_ands * sizeof(YaoGate));
	long counter = party.get_gate_id();
	map<string, Timer> timers;
	SeededPRNG prng;
	and_(processor.S, args, 0, n_args, total_ands, gate, counter,
			prng, timers, repeat, party);
	party.counter += counter - party.get_gate_id();
}

void YaoEvalWire::and_(GC::Memory<GC::Secret<YaoEvalWire> >& S,
		const vector<int>& args, size_t start, size_t end, size_t,
		YaoGate* gates, long& gate_id, PRNG&, map<string, Timer>&,
		bool repeat, YaoEvaluator& evaluator)
{
	int dl = GC::Secret<YaoEvalWire>::default_length;
	MMO& mmo = evaluator.mmo;
	for (auto it = args.begin() + start; it < args.begin() + end; it += 4)
	{
		if (*it == 1)
		{
			Key label[YaoGate::N_EVAL_HASHES];
			Key hash[YaoGate::N_EVAL_HASHES];
			gate_id++;
			YaoGate::eval_inputs(label,
					S[*(it + 2)].get_reg(0).key(),
					S[*(it + 3)].get_reg(0).key(),
					gate_id);
			mmo.hash<YaoGate::N_EVAL_HASHES>(hash, label);
			auto& out = S[*(it + 1)];
			out.resize_regs(1);
			YaoGate& gate = *gates;
			gates++;
			gate.eval(out.get_reg(0), hash, S[*(it + 2)].get_reg(0),
					S[*(it + 3)].get_reg(0));
		}
		else
		{
			int n_units = DIV_CEIL(*it, dl);
			for (int j = 0; j < n_units; j++)
			{
				auto& left = S[*(it + 2) + j];
				auto& right = S[*(it + 3) + (repeat ? 0 : j)];
				auto& out = S[*(it + 1) + j];
				int n = min(dl, *it - j * dl);
				out.resize_regs(n);
				for (int k = 0; k < n; k++)
				{
					Key label[YaoGate::N_EVAL_HASHES];
					Key hash[YaoGate::N_EVAL_HASHES];
					auto& left_wire = left.get_reg(k);
					auto& right_key = right.get_reg(repeat ? 0 : k).key();
					gate_id++;
					YaoGate::eval_inputs(label, left_wire.key(), right_key,
							gate_id);
					mmo.hash<YaoGate::N_EVAL_HASHES>(hash, label);
					auto& right_wire = right.get_reg(repeat ? 0 : k);
					YaoGate& gate = *gates;
					gates++;
					gate.eval(out.get_reg(k), hash, left_wire, right_wire);
				}
			}
		}
	}
}

template<class T>
void YaoEvalWire::my_input(T& inputter, bool value, int n_bits)
{
	assert(n_bits == 1);
	auto& inputs = inputter.inputs;
	size_t start = inputs.size();
	inputs.resize(start + 1);
	inputs.set_bit(start, value);
}

template<class T>
void YaoEvalWire::finalize_input(T& inputter, int from, int n_bits)
{
	assert(n_bits == 1);

	if (from == 1)
	{
		auto& i_bit = inputter.i_bit;
		Key key;
		inputter.os.unserialize(key);
		set(key ^ inputter.evaluator.ot_ext.receiverOutputMatrix[i_bit],
				inputter.inputs.get_bit(i_bit));
		i_bit++;
	}
	else
	{
		set(0);
	}
}

void YaoEvalWire::inputb(GC::Processor<GC::Secret<YaoEvalWire> >& processor,
        const vector<int>& args)
{
	YaoEvalInput inputter;
	processor.inputb(inputter, processor, args, inputter.evaluator.P->my_num());
	return;
}

void YaoEvalWire::inputbvec(GC::Processor<GC::Secret<YaoEvalWire> >& processor,
        ProcessorBase& input_processor, const vector<int>& args)
{
    YaoEvalInput inputter;
    processor.inputbvec(inputter, input_processor, args,
            inputter.evaluator.P->my_num());
    return;
}

void YaoEvalWire::op(const YaoEvalWire& left, const YaoEvalWire& right,
		Function func)
{
    (void)func;
	YaoGate gate;
	YaoEvaluator::s().load_gate(gate);
	YaoEvaluator::s().counter++;
	gate.eval(*this, left, right);
}

bool YaoEvalWire::get_output()
{
	YaoEvaluator::s().taint();
	bool res = external() ^ YaoEvaluator::s().output_masks.pop_front();
	return res;
}

uint8_t YaoEvalWire::get_output(std::size_t n) {
	YaoEvaluator::s().taint();
	uint8_t decode = YaoEvaluator::s().output_masks.pop_front();
	uint8_t res = key_.get_signal(n) ^ decode;
	return res;
}

void YaoEvalWire::set(const Key& key)
{
	this->key_ = key;
}

void YaoEvalWire::set(Key key, bool external)
{
	assert(key.get_signal() == external);
	set(key);
}

void YaoEvalWire::convcbit(Integer& dest, const GC::Clear& source,
		GC::Processor<GC::Secret<YaoEvalWire>>&)
{
	auto& evaluator = YaoEvaluator::s();
	dest = source;
	evaluator.P->send_long(0, source.get());
	throw needs_cleaning();
}

void YaoEvalWire::projs(GC::Processor<GC::Secret<YaoEvalWire>> &processor, const vector<int>& args) {
	projs_multithread(processor, args);
}

void YaoEvalWire::projs_singlethread(GC::Memory<GC::Secret<YaoEvalWire>> &S, const vector<int> &args, Key *gate_ptr, std::size_t start, std::size_t end, PRNG &, YaoEvaluator &evaluator, long counter) {
	std::size_t source_size = args[2];
	int dl = GC::Secret<YaoEvalWire>::default_length;
	for(std::size_t i=start; i<end; i += 3) {
		int n = args[i];
		// if n > the default register size, e.g. 64, the operation uses n_units registers of size 64
		int n_units = DIV_CEIL(n, dl);
		for(int k=0; k < n_units; k++) {
			auto &dest = S[args[i+1]+k];
			auto &src = S[args[i+2]+k];
			int nk = min(dl, n - k*dl);
			dest.resize_regs(nk);
			for(int j=0; j<nk; j++) {
				YaoEvalWire &dest_wire = dest.get_reg(j);
				const YaoEvalWire &src_wire = src.get_reg(j);
				YaoProjGate gate(source_size, gate_ptr);
				gate.eval(evaluator.mmo, dest_wire, src_wire, counter);
				gate_ptr += gate.garbled_table_size();
				counter++;
			}
		}

	}
}

void YaoEvalWire::projs_multithread(GC::Processor<GC::Secret<YaoEvalWire> >& processor, const vector<int>& args)
{
	YaoEvaluator& party = YaoEvaluator::s();
	int source_size = args[2];
	int threshold = 1024;
	std::size_t proj_size = YaoProjGate::sizeof_table(source_size);
	int tt_len = DIV_CEIL(1 << source_size, 4);
	int total = count_proj_args(args, 3+tt_len);
	if (total < threshold)
	{
		// run in single thread
		Key *gate_ptr = (Key*) party.gates.consume(total * proj_size);
		SeededPRNG prng;
		projs_singlethread(processor.S, args, gate_ptr, 3+tt_len, args.size(), prng, party, party.counter);
		party.counter += total;
		return;
	}

	processor.complexity += total;
	int i_thread = 0;
	size_t start = 3+tt_len;
	for (auto& x : party.get_splits(args, threshold, total, 3+tt_len, 3))
	{
		auto n_gates = x[0];
		auto end = x[1];
		Key* gate_ptr = (Key*) party.gates.consume(n_gates * proj_size);
		party.jobs[i_thread++]->dispatch(processor, args, start,
					end, source_size, gate_ptr, party.get_gate_id());
		party.counter += n_gates;
		start = end;
	}
	party.wait(i_thread);
}

void YaoEvalWire::XOR(const YaoEvalWire &x, const YaoEvalWire &y) {
	set(x.key() ^ y.key());
}

void YaoEvalWire::XOR(const YaoEvalWire &x, bool) {
	// the label representing the constant is chosen to be 0
	set(x.key());
}

void YaoEvalWire::XOR(int, const YaoEvalWire &x, const GC::Clear&) {
	// the label representing the constant is chosen to be 0
	set(x.key());
}

void YaoEvalWire::convcbit2s(GC::Processor<whole_type>& processor,
		const BaseInstruction& instruction)
{
	int unit = GC::Clear::N_BITS;
	for (int i = 0; i < DIV_CEIL(instruction.get_n(), unit); i++)
	{
		auto& dest = processor.S[instruction.get_r(0) + i];
		dest.resize_regs(min(unsigned(unit), instruction.get_n() - i * unit));
		for (auto& reg : dest.get_regs())
			reg.set(0);
	}
}

template void YaoEvalWire::and_<false>(
        GC::Processor<GC::Secret<YaoEvalWire> >& processor,
        const vector<int>& args);
template void YaoEvalWire::and_<true>(
        GC::Processor<GC::Secret<YaoEvalWire> >& processor,
        const vector<int>& args);
