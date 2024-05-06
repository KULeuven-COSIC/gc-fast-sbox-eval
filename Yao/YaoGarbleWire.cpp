/*
 * YaoWire.cpp
 *
 */

#include "YaoGarbleWire.h"
#include "YaoGate.h"
#include "YaoGarbler.h"
#include "YaoGarbleInput.h"
#include "GC/ArgTuples.h"

#include "GC/Processor.hpp"
#include "GC/Secret.hpp"
#include "GC/Thread.hpp"
#include "GC/ShareSecret.hpp"
#include "YaoCommon.hpp"

#include "YaoProjGate.h"

void YaoGarbleWire::random()
{
	if (YaoGarbler::s().prng.get_bit())
		key_ = YaoGarbler::s().get_delta();
	else
		key_ = 0;
}

void YaoGarbleWire::public_input(bool value)
{
	key_ = YaoGate::garble_public_input(value, YaoGarbler::s().get_delta());
}

void YaoGarbleWire::and_(GC::Processor<GC::Secret<YaoGarbleWire> >& processor,
		const vector<int>& args, bool repeat)
{
#ifdef YAO_TIMINGS
	auto& garbler = YaoGarbler::s();
	TimeScope ts(garbler.and_timer), ts2(garbler.and_proc_timer),
			ts3(garbler.and_main_thread_timer);
#endif
	and_multithread(processor, args, repeat);
}

void YaoGarbleWire::and_multithread(GC::Processor<GC::Secret<YaoGarbleWire> >& processor,
		const vector<int>& args, bool repeat)
{
	YaoGarbler& party = YaoGarbler::s();
	int total = processor.check_args(args, 4);
	if (total < party.get_threshold())
	{
		// run in single thread
		and_singlethread(processor, args, repeat);
		return;
	}

	party.and_prepare_timer.start();
	processor.complexity += total;
	SendBuffer& gates = party.gates;
	gates.allocate(total * sizeof(YaoGate));
	int i_thread = 0, start = 0;
	for (auto& x : party.get_splits(args, party.get_threshold(), total, 0, 4))
	{
		int i_gate = x[0];
		int end = x[1];
		YaoGate* gate = (YaoGate*)gates.end();
		gates.skip(i_gate * sizeof(YaoGate));
		party.timers["Dispatch"].start();
		party.jobs[i_thread++]->dispatch(YAO_AND_JOB, processor, args, start,
				end, i_gate, gate, party.get_gate_id(), repeat);
		party.timers["Dispatch"].stop();
		party.counter += i_gate;
		i_gate = 0;
		start = end;
	}
	party.and_prepare_timer.stop();
	party.and_wait_timer.start();
	party.wait(i_thread);
	party.and_wait_timer.stop();
}

void YaoGarbleWire::and_singlethread(GC::Processor<GC::Secret<YaoGarbleWire> >& processor,
		const vector<int>& args, bool repeat)
{
	int total_ands = processor.check_args(args, 4);
	if (total_ands < 10)
		return processor.and_(args, repeat);
	processor.complexity += total_ands;
	size_t n_args = args.size();
	auto& garbler = YaoGarbler::s();
	SendBuffer& gates = garbler.gates;
	YaoGate* gate = (YaoGate*)gates.allocate_and_skip(total_ands * sizeof(YaoGate));
	long counter = garbler.get_gate_id();
	and_(processor.S, args, 0, n_args, total_ands, gate, counter,
			garbler.prng, garbler.timers, repeat, garbler);
	garbler.counter += counter - garbler.get_gate_id();
}

void YaoGarbleWire::and_(GC::Memory<GC::Secret<YaoGarbleWire> >& S,
		const vector<int>& args, size_t start, size_t end, size_t,
		YaoGate* gate, long& counter, PRNG& prng, map<string, Timer>& timers,
		bool repeat, YaoGarbler& garbler)
{
	(void)timers;
	const Key& delta = garbler.get_delta();
	int dl = GC::Secret<YaoGarbleWire>::default_length;
	Key left_delta = delta.doubling(1);
	Key right_delta = delta.doubling(2);
	Key labels[4];
	Key hashes[4];
	MMO& mmo = garbler.mmo;
	for (auto it = args.begin() + start; it < args.begin() + end; it += 4)
	{
		if (*it == 1)
		{
			counter++;
			YaoGate::E_inputs(labels, S[*(it + 2)].get_reg(0),
					S[*(it + 3)].get_reg(0), left_delta, right_delta,
					counter);
			mmo.hash<4>(hashes, labels);
			auto& out = S[*(it + 1)];
			out.resize_regs(1);
			YaoGate::randomize(out.get_reg(0), prng);
			(gate++)->and_garble(out.get_reg(0), hashes,
					S[*(it + 2)].get_reg(0),
					S[*(it + 3)].get_reg(0), garbler.get_delta());
		}
		else
		{
			int n_units = DIV_CEIL(*it, dl);
			for (int j = 0; j < n_units; j++)
			{
				auto& out = S[*(it + 1) + j];
				int left = min(dl, *it - j * dl);
				out.resize_regs(left);
				for (int k = 0; k < left; k++)
				{
					auto& left_wire = S[*(it + 2) + j].get_reg(k);
					auto& right_wire = S[*(it + 3) + j].get_reg(
							repeat ? 0 : k);
					counter++;
					YaoGate::E_inputs(labels, left_wire,
							right_wire, left_delta, right_delta, counter);
					mmo.hash<4>(hashes, labels);
					//timers["Inner ref"].start();
					//timers["Inner ref"].stop();
					//timers["Randomizing"].start();
					out.get_reg(k).randomize(prng);
					//timers["Randomizing"].stop();
					//timers["Gate computation"].start();
					(gate++)->and_garble(out.get_reg(k), hashes,
							left_wire, right_wire,
							garbler.get_delta());
					//timers["Gate computation"].stop();
				}
			}
		}
	}
}


void YaoGarbleWire::inputb(GC::Processor<GC::Secret<YaoGarbleWire>>& processor,
        const vector<int>& args)
{
	auto& garbler = YaoGarbler::s();
	YaoGarbleInput input;
	processor.inputb(input, processor, args, garbler.P->my_num());
}

void YaoGarbleWire::inputbvec(GC::Processor<GC::Secret<YaoGarbleWire>>& processor,
        ProcessorBase& input_processor, const vector<int>& args)
{
    auto& garbler = YaoGarbler::s();
    YaoGarbleInput input;
    processor.inputbvec(input, input_processor, args, garbler.P->my_num());
}

inline void YaoGarbler::store_gate(const YaoGate& gate)
{
	gates.serialize(gate);
}

void YaoGarbleWire::op(const YaoGarbleWire& left, const YaoGarbleWire& right,
		Function func)
{
	auto& garbler = YaoGarbler::s();
	randomize(garbler.prng);
	YaoGarbler::s().counter++;
	YaoGate gate(*this, left, right, func);
	YaoGarbler::s().store_gate(gate);
}

char YaoGarbleWire::get_output()
{
	YaoGarbler::s().taint();
	YaoGarbler::s().output_masks.push_back(mask());
	return 0;
}

uint8_t YaoGarbleWire::get_output(std::size_t n) {
	YaoGarbler::s().taint();
	YaoGarbler::s().output_masks.push_back(key_.get_signal(n));
	return 0;
}

void YaoGarbleWire::convcbit(Integer& dest, const GC::Clear& source,
		GC::Processor<GC::Secret<YaoGarbleWire>>&)
{
	(void) source;
	auto& garbler = YaoGarbler::s();
	garbler.untaint();
	dest = garbler.P->receive_long(1);
}

void YaoGarbleWire::projs(GC::Processor<GC::Secret<YaoGarbleWire>> &processor, const vector<int>& args) {
	projs_multithread(processor, args);
}

void YaoGarbleWire::projs_singlethread(GC::Memory<GC::Secret<YaoGarbleWire>> &S, const vector<int>& args, Key *gate_ptr, std::size_t start, std::size_t end, PRNG &prng, YaoGarbler &garbler, long counter) {
	std::size_t source_size = args[2];
	auto& in_deltas = garbler.get_deltas(source_size);
	auto& out_deltas = garbler.get_deltas(args[1]);
	int dl = GC::Secret<YaoGarbleWire>::default_length;
	for(std::size_t i=start; i < end; i+=3) {
		int n = args[i];
		// if n > the default register size, e.g. 64, the operation uses n_units registers of size 64
		int n_units = DIV_CEIL(n, dl);
		for(int k=0; k < n_units; k++) {
			auto &dest = S[args[i+1]+k];
			auto &src = S[args[i+2]+k];
			int nk = min(dl, n - k*dl);
			dest.resize_regs(nk);
			for(int j=0; j<nk; j++) {
				YaoGarbleWire &dest_wire = dest.get_reg(j);
				const YaoGarbleWire &src_wire = src.get_reg(j);
				YaoProjGate gate(source_size, gate_ptr);
				gate.garble(prng, garbler.mmo, dest_wire, src_wire, args, 3, in_deltas, out_deltas, counter);
				gate_ptr += gate.garbled_table_size();
				counter++;
			}
		}

	}
}

void YaoGarbleWire::projs_multithread(GC::Processor<GC::Secret<YaoGarbleWire>> &processor, const vector<int>& args) {
	YaoGarbler& party = YaoGarbler::s();
	int source_size = args[2];
	SendBuffer& gates = party.gates;
	std::size_t proj_size = YaoProjGate::sizeof_table(source_size);
	int tt_len = DIV_CEIL(1 << source_size, 4);
	int total = count_proj_args(args, 3+tt_len);
	gates.allocate(total * proj_size);
	if (total < (party.get_threshold() >> (std::max(0, (int)(source_size) - 2))))
	{
		// run in single thread
		Key *gate_ptr = (Key*) gates.end();
		projs_singlethread(processor.S, args, gate_ptr, 3+tt_len, args.size(), party.prng, party, party.get_gate_id());
		gates.skip(total * proj_size);
		party.counter += total;
		return;
	}

	processor.complexity += total;
	int i_thread = 0;
	size_t start = 3+tt_len;
	for (auto& x : party.get_splits(args, party.get_threshold(), total, 3+tt_len, 3))
	{
		size_t n_gates = x[0];
		size_t end = x[1];
		Key *gate = (Key*)gates.end();
		gates.skip(n_gates * proj_size);
		party.timers["Dispatch"].start();
		party.jobs[i_thread++]->dispatch(processor, args, start, end, source_size, gate, party.get_gate_id());
		party.timers["Dispatch"].stop();
		party.counter += n_gates;
		start = end;
	}
	party.wait(i_thread);
}

void YaoGarbleWire::XOR(const YaoGarbleWire &x, const YaoGarbleWire &y) {
	set_full_key(x.full_key() ^ y.full_key());
}

void YaoGarbleWire::XOR(const YaoGarbleWire &x, bool y) {
	set_full_key(y ? x.full_key() ^ YaoGarbler::s().get_delta() : x.full_key() );
}

void YaoGarbleWire::XOR(int n, const YaoGarbleWire &x, const GC::Clear &y) {
	assert(y.get() <= 0xff);
	set_full_key(x.full_key() ^ Key::prod(y.get(), YaoGarbler::s().get_deltas(n)));
}

void YaoGarbleWire::convcbit2s(GC::Processor<whole_type>& processor,
		const BaseInstruction& instruction)
{
	int unit = GC::Clear::N_BITS;
	for (int i = 0; i < DIV_CEIL(instruction.get_n(), unit); i++)
	{
		auto& dest = processor.S[instruction.get_r(0) + i];
		int n = min(unsigned(unit), instruction.get_n() - i * unit);
		dest.resize_regs(n);
		for (int j = 0; j < n; j++)
			dest.get_reg(i).public_input(
					processor.C[instruction.get_r(1) + i].get_bit(j));
	}
}
