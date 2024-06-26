/*
 * AddableVector.cpp
 *
 */

#include "AddableVector.h"
#include "Rq_Element.h"
#include "FHE_Keys.h"

template<class T>
AddableVector<T> AddableVector<T>::mul_by_X_i(int j,
        const FHE_PK& pk) const
{
    int phi_m = this->size();
    assert(phi_m == pk.get_params().phi_m());
    AddableVector res(phi_m);
    for (int i = 0; i < phi_m; i++)
    {
        int k = j + i, s = 1;
        while (k >= phi_m)
        {
            k -= phi_m;
            s = -s;
        }
        if (s == 1)
        {
            res[k] = (*this)[i];
        }
        else
        {
            res[k] = -(*this)[i];
        }
    }
    return res;
}

template
AddableVector<Int_Random_Coins::rand_type> AddableVector<
        Int_Random_Coins::rand_type>::mul_by_X_i(int j, const FHE_PK& pk) const;
