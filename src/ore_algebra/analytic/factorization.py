# -*- coding: utf-8 - vim: tw=80
"""
Symbolic-numeric algorithm for the factorization of linear differential
operators.
"""

# Copyright 2021 Alexandre Goyer, Inria Saclay Ile-de-France
#
# Distributed under the terms of the GNU General Public License (GPL) either
# version 2, or (at your option) any later version
#
# http://www.gnu.org/licenses/

import collections

from sage.rings.rational_field import QQ
from sage.rings.integer_ring import ZZ
from sage.rings.real_mpfr import RealField
from sage.rings.qqbar import QQbar
from sage.rings.power_series_ring import PowerSeriesRing
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.laurent_series_ring import LaurentSeriesRing
from sage.modules.free_module_element import vector
from sage.misc.misc_c import prod
from sage.arith.functions import lcm
from sage.functions.other import binomial
from sage.arith.misc import valuation, gcd
from sage.misc.misc import cputime
from sage.plot.line import line2d

from ore_algebra.guessing import guess

from .monodromy import _monodromy_matrices
from .differential_operator import PlainDifferentialOperator
from .accuracy import PrecisionError
from .complex_optimistic_field import ComplexOptimisticField
from .utilities import (customized_accuracy, power_series_coerce, derivatives,
                        hp_approximants, guess_exact_numbers)
from .linear_algebra import invariant_subspace


Radii = RealField(30)

MonoData = collections.namedtuple("MonoData", ["precision", "matrices", "points", "loss"])
NewtonEdge = collections.namedtuple("NewtonEdge", ["slope", "startpoint", "length", "polynomial"])

class LinearDifferentialOperator(PlainDifferentialOperator):

    r"""
    A subclass of linear differential operators for internal use.
    Assumptions: polynomial coefficients and 0 is an ordinary point.
    """

    def __init__(self, dop):

        if not dop:
            raise ValueError("operator must be nonzero")
        if not dop.parent().is_D():
            raise ValueError("expected an operator in K(x)[D]")
        _, _, _, dop = dop.numerator()._normalize_base_ring()
        den = lcm(c.denominator() for c in dop)
        dop *= den
        super(LinearDifferentialOperator, self).__init__(dop)

        self.z = self.base_ring().gen()
        self.Dz = self.parent().gen()
        self.n = self.order()

        self.order_of_truncation = max(100, 2*self.degree() + self.n)
        self.algebraicity_degree = self.base_ring().base_ring().degree()
        self.precision = 100 #100*self.algebraicity_degree

        self.monodromy_data = MonoData(0, [], None, 0)

        self.fuchsian_info = None


    def is_fuchsian(self):

        r"""
        Return True if "self" is fuchian, False otherwise.

        Fuch's criterion: p is a regular point of a_n*Dz^n + ... + a_0 (with a_i
        polynomial) iff no (z-p)^{n-k}*a_k/a_n admits p as pole.
        """

        coeffs = self.coefficients()
        fac = coeffs.pop().factor()
        for (f, m) in fac:
            for k, ak in enumerate(coeffs):
                mk = valuation(ak, f)
                if mk - m < k - self.n: return False

        dop = self.annihilator_of_composition(1/self.z)
        for k, frac in enumerate(dop.monic().coefficients()[:-1]):
            d = (self.z**(self.n - k)*frac).denominator()
            if d(0)==0: return False

        return True


    def monodromy(self, precision, verbose=False):

        r"""
        Compute a generating set of matrices for the monodromy group of "self"
        at 0, such that the (customized) precision of each coefficient is at
        least equal to "precision".
        """

        if verbose: print("Monodromy computation with wanted precision = " + str(precision) + ".")
        if self.monodromy_data.precision<precision:
            success, increment, loss = False, 50, self.monodromy_data.loss
            if self.monodromy_data.points==None:
                useful_singularities = self._singularities(QQbar, include_apparent=False)
            else:
                useful_singularities = self.monodromy_data.points
            while not success:
                try:
                    p = precision + loss + increment
                    if verbose: print("Try with precision = " + str(p) + ".")
                    it = _monodromy_matrices(self, 0, eps=Radii.one()>>p, sing=useful_singularities)
                    points, matrices = [], []
                    for pt, mat, is_scalar in it:
                        if not is_scalar: matrices.append(mat); points.append(pt)
                    output_precision = min(min([customized_accuracy(mat.list()) for mat in matrices], default=p), p)
                    if output_precision<precision:
                        if verbose: print("Insufficient precision, loss = " + str(p - output_precision) + ".")
                        increment = 50 if loss==0 else increment<<1
                    else: success=True
                    loss = max(loss, p - output_precision)
                except (ZeroDivisionError, PrecisionError):
                    if verbose: print("Insufficient precision for computing monodromy.")
                    increment = increment<<1
            self.monodromy_data =  MonoData(output_precision, matrices, points, loss)


    def _symbolic_guessing(self):

        """
        Return a non-trivial right factor under the assumtion that the elements
        of the differential Galois group of "self" are homotheties.
        """

        T = self.order_of_truncation
        R = self.base_ring().base_ring()

        while True:

            S = PowerSeriesRing(R, default_prec=T + 1)
            basis = self.local_basis_expansions(QQ.zero(), T + 1) # computing only the first one?
            f = power_series_coerce(basis[0], S)
            pols = hp_approximants([f, f.derivative()], T)
            dop = self.parent()(pols)
            if self%dop==0: return dop
            T = T<<1


    def _guessing(self, v, m):

        """
        Return a non-trivial right factor thanks to an oracle that indicates a
        good linear combination of the solutions of "self" at 0, that is, a
        solution annihilating an operator of smaller order than "self".
        """

        T0, T, d0 = 25, self.order_of_truncation, 0
        p = customized_accuracy(v)
        if p<50: raise PrecisionError("Loosing too much precision to attempt the guessing part.")
        C = ComplexOptimisticField(p, eps=Radii.one()>>p//3)
        v = v.change_ring(C)

        while T0<=2*T:

            S = PowerSeriesRing(C, default_prec=T0 + m)
            basis = self.local_basis_expansions(QQ.zero(), T0 + m) # avoiding the re-computation of the first terms?
            basis = power_series_coerce(basis, S)
            f = v*vector(basis)
            pols = hp_approximants(derivatives(f, m), T0)
            p, d1 = customized_accuracy(pols), max(pol.degree() for pol in pols)
            if d1==d0:
                alg_deg = self.algebraicity_degree
                while 50*alg_deg<p:
                    try:
                        exact_pols = guess_exact_numbers(pols, alg_deg)
                        coeffs = [c for pol in exact_pols for c in pol.coefficients()]
                        selftilde = self.extend_scalars(*coeffs)[0] # not recursive, need an embedding
                        dop = selftilde.parent()(exact_pols)
                        if selftilde%dop==0:
                            self, self.algebraicity_degree = selftilde, alg_deg
                            self.z, self.Dz = self.base_ring().gen(), self.parent().gen()
                            return dop
                    except PrecisionError: pass
                    alg_deg = alg_deg + 1
            d0, T0 = d1, T0<<1

        self.order_of_truncation = self.order_of_truncation<<1

        raise PrecisionError("Insufficient precision for the guessing part.")


    def right_factor(self, verbose=False):

        r"""
        Return either a non-trivial right factor of "self" or the string
        'irreducible' if "self" is irreducible.
        """

        if self.n<2: return 'irreducible'
        if verbose: print("Try to factorize an operator of order " + str(self.n) + ".")
        if self.fuchsian_info==None:
            self.fuchsian_info = self.is_fuchsian()
            if not self.fuchsian_info: print("WARNING: The operator is not fuchsian: termination is not guaranteed.")

        self.monodromy(self.precision, verbose=verbose)
        self.precision = self.monodromy_data.precision
        matrices = self.monodromy_data.matrices
        if verbose: print("Monodromy computed with precision = " + str(self.precision) + ".")

        if matrices==[]:
            if verbose: print("Any subspace is invariant --> symbolic guessing.")
            dop = self._symbolic_guessing()
        else:
            try:
                V = invariant_subspace(matrices, verbose=verbose)
                if V is None: return 'irreducible'
                if verbose: print("Find an invariant subspace of dimension " + str(len(V)) + " --> guessing.")
                dop = self._guessing(V[0], len(V))
            except PrecisionError:
                if verbose: print("Insufficient precision.")
                self.precision = self.precision<<1
                return self.right_factor(verbose=verbose)

        return dop


    def euler_rep(self):

        z, n = self.z, self.n; coeffs = self.list()
        output = [ coeffs[0] ] + [0]*n
        l = [0] # coefficients of T(T-1)...(T-k+1) (initial: k=0)

        for k in range(1, n+1):

            newl = [0]
            for i in range(1, len(l)):
                newl.append((-k+1)*l[i]+l[i-1])
            l = newl + [1]

            ck = coeffs[k]
            for j in range(1, k+1):
                output[j] += ck*z**(-k)*l[j]

        return output



def try_rational(dop):

    for (f,) in dop.rational_solutions():
        d = f.gcd(f.derivative())
        rfactor = (f/d)*dop.parent().gen() - f.derivative()/d
        return rfactor

    return None


def right_factor(dop, verbose=False, hybrid=True):

    r"""
    Return either a non-trivial right factor of "dop" or the string
    'irreducible' if "dop" is irreducible.
    """

    if dop.order()<2: return 'irreducible'
    rfactor = try_rational(dop)
    if not rfactor is None: return rfactor
    if hybrid:
        rfactor = try_vanHoeij(dop)
        if not rfactor is None: return rfactor

    coeffs, z0, z = dop.monic().coefficients(), QQ.zero(), dop.base_ring().gen()
    while min(c.valuation(z - z0) for c in coeffs)<0: z0 = z0 + QQ.one()
    shifted_dop = LinearDifferentialOperator(dop.annihilator_of_composition(z + z0))

    output = shifted_dop.right_factor(verbose=verbose)
    if output=='irreducible': return 'irreducible'
    output = output.annihilator_of_composition(z - z0)
    return output


def _factor(dop, verbose=False, hybrid=True):

    rfactor = right_factor(dop, verbose=verbose, hybrid=hybrid)
    if rfactor=='irreducible': return [dop]
    lfactor = rfactor.parent()(dop)//rfactor
    return _factor(lfactor, verbose=verbose, hybrid=hybrid) + _factor(rfactor, verbose=verbose, hybrid=hybrid)


def factor(dop, verbose=False, hybrid=True):

    r"""
    Return a list of irreductible operators [L1, L2, ..., Lr] such that L is
    equal to the composition L1.L2...Lr.
    """

    output = _factor(dop, verbose=verbose, hybrid=hybrid)
    K0, K1 = output[0].base_ring().base_ring(), output[-1].base_ring().base_ring()
    if K0 != K1:
        A = output[0].parent()
        output = [A(f) for f in output]
    return output


def my_newton_polygon(dop):

    r"""
    Computes the Newton polygon of ``self`` at 0.

    INPUT:

      - ``dop`` -- a linear differential operator which polynomial coefficients

    OUTPUT:

    EXAMPLES::

    """

    n = dop.order(); z = dop.base_ring().gen()
    Pols, X = PolynomialRing(QQ, 'X').objgen()

    points = [ ((QQ(i), QQ(c.valuation(z))), c.coefficients()[0]) \
               for i, c in enumerate(dop.to_T('Tz').list()) if c!=0 ]

    (i1, j1), c1 = points[0]
    for (i, j), c in points:
        if j<=j1: (i1, j1), c1 = (i, j), c

    Edges = []
    if i1>0:
        poly = dop.indicial_polynomial(z, var = 'X')

        #pol = c1*X**i1
        #for (i, j), c in points:
        #    if i<i1 and j==j1: pol += c*X**i
        ## it is the same think (pol = poly)

        Edges.append( NewtonEdge(QQ(0), (0, j1), i1, poly) )

    while i1<n:
        poly = c1; (i2, j2), c2 = points[-1]; s = (j2 - j1)/(i2 - i1)
        for (i, j), c in points:
            if i>i1:
                t = (j - j1)/(i - i1)
                if t<s:
                    poly = c1; s = t
                    if t<=s:
                        poly += c*X**((i - i1)//s.denominator()) # REDUCED characteristic polynomial
                        (i2, j2), c2 = (i, j), c
        Edges.append( NewtonEdge(s, (i1, j1), i2 - i1, poly) )
        (i1, j1), c1 = (i2, j2), c2

    return Edges


def display_newton_polygon(dop):

    Edges = my_newton_polygon(dop)

    (i, j) = Edges[0].startpoint
    L1 = line2d([(i - 3, j), (i, j)], thickness=3)
    e = Edges[-1]; s = e.slope; (i,j) = e.startpoint; l = e.length
    L2 = line2d([(i + l, j + l*s), (i + l, j + l*s + 3)], thickness=3)

    L = sum(line2d([e.startpoint, (e.startpoint[0] + e.length, e.startpoint[1] \
            + e.length*e.slope)], marker='o', thickness=3) for e in Edges)

    return L1 + L + L2


def exponents(dop, multiplicities=True):

    if dop.base_ring().base_ring()==QQ:
        FLS = LaurentSeriesRing(QQ, dop.base_ring().variable_name())
    else:
        FLS = LaurentSeriesRing(QQbar, dop.base_ring().variable_name())
    l = LinearDifferentialOperator(dop).euler_rep()
    if FLS.base_ring()==QQ:
        l = [FLS(c) for c in l]
    else:
        Pol, _ = PolynomialRing(QQbar, dop.base_ring().variable_name()).objgen()
        l = [FLS(Pol.fraction_field()(c)) for c in l]
    vmin = min(c.valuation() for c in l)
    Pols, X = PolynomialRing(QQ, 'X').objgen()
    pol = sum(FLS.base_ring()(c.coefficients()[0])*X**i for i, c in enumerate(l) if c.valuation()==vmin)
    r = pol.roots(QQbar, multiplicities=multiplicities)

    return r


def S(dop, e):
    """ map: Tz --> Tz + e """

    l = LinearDifferentialOperator(dop).euler_rep()
    for i, c in enumerate(l):
        for k in range(i):
            l[k] += binomial(i, k)*e**(i - k)*c
    T = dop.base_ring().gen()*dop.parent().gen()
    output = sum(c*T**i for i, c in enumerate(l))

    return output

def search_exp_part_with_mult1(dop):

    dop = LinearDifferentialOperator(dop)
    lc = dop.leading_coefficient()//gcd(dop.list())
    for f, _ in list(lc.factor()) + [ (1/dop.base_ring().gen(), None) ]:
        pol = dop.indicial_polynomial(f)
        roots = pol.roots(QQbar)
        for r, m in roots:
            if m==1:
                success = True
                for s, l in roots:
                    if s!=r and r-s in ZZ: success = False
                if success: return (f, r)

    return (None, None)

def guessing_via_series(L, einZZ):
    """ assumption: 0 is an exponential part of multiplicity 1 (at 0) """
    if not einZZ: # if e in ZZ, this test has already been done
        R = try_rational(L)
        if not R is None: return R
    r = L.order(); A = L.parent()
    t = len(L.desingularize().leading_coefficient().roots(QQbar))
    b = min(1000, max(50, (r - 1)**2*(r - 2)*(t - 1)))
    try:
        R = guess(L.power_series_solutions(b)[0].list(), A, order=r - 1)
        if 0<R.order()<r and L%R==0: return R
    except ValueError: pass
    La = L.adjoint()
    Ra = try_rational(La)
    if not Ra is None: return (La//Ra).adjoint()
    ea = ZZ([e for e in exponents(La, False) if e in ZZ][0]); La = S(La, ea)
    try:
        Ra = guess(La.power_series_solutions(b)[0].list(), A, order=r - 1)
        if 0<Ra.order()<r and La%Ra==0: return S(La//Ra, -ea).adjoint()
    except ValueError: return None



def try_vanHoeij(L):
    """ try to find a factor thank to an exponential part of multiplicity 1 """
    z, (p, e) = L.base_ring().gen(), search_exp_part_with_mult1(L)
    if p==None: return None
    if (p*z).is_one():
        L = L.annihilator_of_composition(p)
        e = search_exp_part_with_mult1(L)[1]
        L, e = LinearDifferentialOperator(L).extend_scalars(e)
        L = S(L, e)
    elif p.degree()==1:
        s = -p[0]/p[1]
        L, e = LinearDifferentialOperator(L).extend_scalars(e)
        L = S(L.annihilator_of_composition(z + s), e)
    else: return None # to be implemented?
    R = guessing_via_series(L, e in ZZ)
    if R==None: return None
    if (p*z).is_one(): return S(R, -e).annihilator_of_composition(p)
    elif p.degree()==1: return S(R, -e).annihilator_of_composition(z - s)