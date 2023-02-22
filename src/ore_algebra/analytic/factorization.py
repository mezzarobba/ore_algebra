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
import tempfile
import cProfile
import pstats

from ore_algebra import guess
from ore_algebra.analytic.accuracy import PrecisionError
from ore_algebra.analytic.complex_optimistic_field import ComplexOptimisticField
from ore_algebra.analytic.differential_operator import PlainDifferentialOperator
from ore_algebra.analytic.linear_algebra import (invariant_subspace,
                                                 row_echelon_form, ker,
                                                 gen_eigenspaces, orbit,
                                                 customized_accuracy)
from ore_algebra.analytic.monodromy import _monodromy_matrices
from ore_algebra.analytic.utilities import as_embedded_number_field_elements
from ore_algebra.guessing import guess
from sage.arith.functions import lcm
from sage.arith.misc import algdep, gcd
from sage.functions.all import log, floor
from sage.functions.other import binomial, factorial
from sage.matrix.constructor import matrix
from sage.matrix.matrix_dense import Matrix_dense
from sage.matrix.special import block_matrix, identity_matrix, diagonal_matrix
from sage.misc.functional import numerical_approx
from sage.misc.misc import cputime
from sage.misc.misc_c import prod
from sage.modules.free_module_element import (vector,
                                              FreeModuleElement_generic_dense)
from sage.rings.integer_ring import ZZ
from sage.rings.laurent_series_ring import LaurentSeriesRing
from sage.rings.qqbar import QQbar
from sage.rings.power_series_ring import PowerSeriesRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField
from sympy.core.numbers import oo

Radii = RealField(30)



def factor(dop, verbose=False):

    r"""
    Return a decomposition of this operator as a product of irreducible
    operators (potentially introducing algebraic extensions).

    NOTE: The termination of this method is currently not garanteed if the
    operator is not Fuchsian.

    INPUT:

    - ``verbose`` - (optional, default: False) - if set to True, this
    method prints some messages about the progress of the computation.

    OUTPUT:

    - ``fac`` - a list of irreducible operators such that the product of
    its elements is equal to the operator ``self``.


    EXAMPLES::

        sage: from ore_algebra.analytic.examples.factor import z, Dz
        sage: dop = Dz*z*Dz
        sage: factor(dop)
        [z*Dz + 1, Dz]

    """

    def _factor(dop, verbose=False):

        R = rfactor(dop, verbose)
        if R==None: return [dop]
        OA = R.parent(); OA = OA.change_ring(OA.base_ring().fraction_field())
        Q = OA(dop)//R
        fac_left = _factor(Q, verbose)
        fac_right = _factor(R, verbose)
        return fac_left + fac_right

    fac = _factor(dop, verbose)
    K0, K1 = fac[0].base_ring().base_ring(), fac[-1].base_ring().base_ring()
    if K0 != K1:
        A = fac[0].parent()
        fac = [A(f) for f in fac]

    return fac

def rfactor(dop, verbose=False):

    r"""
    Return either ``None`` if ``dop`` is irreducible or a proper right-hand
    factor of ``dop`` otherwise (potentially introducing algebraic extensions).

    NOTE: The termination of this method is currently not garanteed if the
    operator is not Fuchsian.

    INPUT:
     -- ``dop``     -- differential operator
     -- ``verbose`` -- (optional, default: False) - if set to True, this
                       method prints some messages about the progress of the
                       computation.

    OUTPUT: either ``None`` or a differential operator

    EXAMPLES::

        sage: from ore_algebra.analytic.factorization import rfactor
        sage: from ore_algebra.analytic.examples.facto import hypergeo_dop
        sage: dop = hypergeo_dop(1,1,1); dop
        (-z^2 + z)*Dz^2 + (-3*z + 1)*Dz - 1
        sage: rfactor(dop).monic()
        Dz + 1/(z - 1)

    """

    z, r = dop.base_ring().gen(), dop.order()
    if r<2:
        return None
    R = _try_rational(dop)
    if R!=None:
        return R

    if verbose:
        print("### Try factoring an operator of order", r)

    s0, sings = QQ.zero(), PlainDifferentialOperator(dop)._singularities(QQbar)
    while s0 in sings: s0 = s0 + QQ.one()
    dop = dop.annihilator_of_composition(z + s0).monic()
    R = rfactor_via_monodromy(dop, verbose=verbose)

    if R==None: return None
    return R.annihilator_of_composition(z - s0)

def rfactor_via_monodromy(dop, order=None, bound=None, alg_degree=None, precision=None, loss=0, verbose=False):

    r"""
    Same as rfactor but focused on the algorithm in [Chyzak, Goyer, Mezzarobba,
    2022].

    EXAMPLES::

        sage: from ore_algebra.analytic.factorization import rfactor_via_monodromy
        sage: from ore_algebra.analytic.examples.facto import hypergeo_dop, z
        sage: dop = hypergeo_dop(1/2,1/3,1/3).annihilator_of_composition(z-1); dop
        (z^2 - 3*z + 2)*Dz^2 + (11/6*z - 13/6)*Dz + 1/6
        sage: rfactor_via_monodromy(dop)
        (2*z - 4)*Dz + 1

    """

    if 0 in PlainDifferentialOperator(dop)._singularities(QQbar): breakpoint()

    r = dop.order()

    if bound==None:
        bound = _degree_bound_for_right_factor(dop)
        if verbose:
            print("Degree bound for right factor", bound)

    if order==None:
        deg_of_dop = PlainDifferentialOperator(dop).degree()
        order = max(min( r*deg_of_dop, 100, bound*(r + 1) + 1 ), 1)
    if alg_degree==None:
        alg_degree = dop.base_ring().base_ring().degree()
    if precision==None:
        precision = 50*(r + 1)

    if verbose:
        print("Current order of truncation", order)
        print("Current working precision", precision, "(before monodromy computation)")
        print("Current algebraic degree", alg_degree)
        print("Start computing monodromy matrices")

    try:
        mono, it = [], _monodromy_matrices(dop, 0, eps=Radii.one()>>precision)
        for pt, mat, scal in it:
            if not scal:
                local_loss = max(0, precision - customized_accuracy(mat))
                if local_loss>loss:
                    loss = local_loss
                    if verbose:
                        print("loss =", loss)
                mono.append(mat)
                if verbose: print(len(mono), "matrices computed")
                conclusive_method = "One_Dimensional"
                R = one_dimensional_eigenspaces(dop, mono, order, bound, alg_degree, verbose)
                if R=="NotGoodConditions":
                    conclusive_method = "Simple_Eigenvalue"
                    R = simple_eigenvalue(dop, mono, order, bound, alg_degree, verbose)
                    if R=="NotGoodConditions":
                        conclusive_method = "Multiple_Eigenvalue"
                        R = multiple_eigenvalue(dop, mono, order, bound, alg_degree, verbose)
                if R!="Inconclusive":
                    if verbose:
                        print("Conclude with " + conclusive_method + " method")
                    try:
                        cond_nb = max([_frobenius_norm(m)*_frobenius_norm(~m) for m in mono])
                        cond_nb = cond_nb.log(10).ceil()
                    except (ZeroDivisionError, PrecisionError):
                        cond_nb = oo
                    return R
        if mono==[]:
            return rfactor_when_monodromy_is_trivial(dop, order, verbose)


    except (ZeroDivisionError, PrecisionError):
        precision += max(150, precision - loss)
        return rfactor_via_monodromy(dop, order, bound, alg_degree, precision, loss, verbose)

    precision += max(150, precision - loss)
    order = min( bound*(r + 1) + 1, order<<1 )
    return rfactor_via_monodromy(dop, order, bound, alg_degree + 1, precision, loss, verbose)

def rfactor_when_monodromy_is_trivial(dop, order, verbose=False):

    r"""
    Same as rfactor_via_monodromy but focused on the case where the monodromy
    group is generated by homotheties.

    EXAMPLES::

        sage: from ore_algebra.analytic.factorization import rfactor_when_monodromy_is_trivial
        sage: from ore_algebra.examples.stdfun import dawson
        sage: dawson.dop, rfactor_when_monodromy_is_trivial(dawson.dop, 10)
        (Dx^2 + 2*x*Dx + 2, 1/2*Dx + x)

    """

    if verbose: print("Galois algebra is trivial: symbolic HP approximants method at order", order)
    K, r = dop.base_ring().base_ring(), dop.order()
    S = PowerSeriesRing(K, default_prec=order + r)
    f = dop.local_basis_expansions(QQ.zero(), order + r)[0]
    f = _formal_finite_sum_to_power_series(f, S)

    der = [ f.truncate() ]
    for k in range(r - 1): der.append( der[-1].derivative() )
    mat = matrix(r, 1, der)
    min_basis = mat.minimal_approximant_basis(max(order//r, 1))
    rdeg = min_basis.row_degrees()
    i0 = min(range(len(rdeg)), key = lambda i: rdeg[i])
    R = dop.parent()(list(min_basis[i0]))
    if dop%R==0: return R

    order = order<<1
    return rfactor_when_monodromy_is_trivial(dop, order, verbose)

def one_dimensional_eigenspaces(dop, mono, order, bound, alg_degree, verbose=False):

    """
    output: a nontrivial right factor R of dop, or None, or ``NotGoodConditions``,
    or ``Inconclusive``
    """

    mat = _random_combination(mono)
    id = mat.parent().one()
    Spaces = gen_eigenspaces(mat)
    conclusive = True
    goodconditions = True
    for space in Spaces:
        eigvalue = space["eigenvalue"]
        eigspace = ker(mat - eigvalue*id)
        if len(eigspace)>1:
            goodconditions = False
            break
        R = annihilator(dop, eigspace[0], order, bound, alg_degree, mono, verbose)
        if R=="Inconclusive": conclusive = False
        if R!=dop: return R
    if not goodconditions: return "NotGoodConditions"
    if conclusive: return None
    return "Inconclusive"

def simple_eigenvalue(dop, mono, order, bound, alg_degree, verbose=False):

    """
    output: a nontrivial right factor R of dop, or None, or ``NotGoodConditions``,
    or ``Inconclusive``

    Assumption: dop is monic.
    """

    mat = _random_combination(mono)
    id = mat.parent().one()
    Spaces = gen_eigenspaces(mat)
    goodconditions = False
    for space in Spaces:
        if space['multiplicity']==1:
            goodconditions = True
            ic = space['basis'][0]
            R = annihilator(dop, ic, order, bound, alg_degree, mono, verbose)
            if R!="Inconclusive" and R!=dop: return R
            adj_dop = myadjoint(dop)
            Q = _transition_matrix_for_adjoint(dop)
            adj_mat = Q * mat.transpose() * (~Q)
            adj_mono = [ Q * m.transpose() * (~Q) for m in mono ]
            eigspace = ker(adj_mat - space['eigenvalue']*id)
            if eigspace==[]: return "Inconclusive"
            if len(eigspace)>1: break # raise PrecisionError?
            adj_ic = eigspace[0]
            adj_Q = annihilator(adj_dop, adj_ic, order, bound, alg_degree, adj_mono, verbose)
            # the bound could have to be changed
            if adj_Q!="Inconclusive" and adj_Q!=adj_dop:
                return myadjoint(adj_dop//adj_Q)
            if R==dop and adj_Q==adj_dop: return None
            break
    if not goodconditions: return "NotGoodConditions"
    return "Inconclusive"

def multiple_eigenvalue(dop, mono, order, bound, alg_degree, verbose=False):
    """
    output: a nontrivial right factor R of dop, or None, or ``Inconclusive``
    """

    r = dop.order()
    invspace = invariant_subspace(mono)
    if invspace==None: return None
    R = annihilator(dop, invspace[0], order, bound, alg_degree, mono, verbose)
    if R!="Inconclusive" and R.order()<r: return R
    return "Inconclusive"

def annihilator(dop, ic, order, bound, alg_degree, mono=None, verbose=False):

    r, OA = dop.order(), dop.parent()
    d = r - 1
    base_field = OA.base_ring().base_ring()

    if mono!=None:
        orb = orbit(mono, ic)
        d = len(orb)
        if d==r: return dop
        ic = _reduced_row_echelon_form(matrix(orb))[0]

    symb_ic, K = _guess_symbolic_coefficients(ic, alg_degree, verbose=verbose)
    if symb_ic!="NothingFound":
        if base_field!=QQ and K!=QQ:
            K = K.composite_fields(base_field)[0]
            symb_ic = [K(x) for x in symb_ic]
        S = PowerSeriesRing(K, default_prec=order + d)
        sol_basis = dop.local_basis_expansions(QQ.zero(), order + d)
        sol_basis = [ _formal_finite_sum_to_power_series(sol, S) for sol in sol_basis ]
        f = vector(symb_ic) * vector(sol_basis)
        if K==QQ and base_field==QQ:
            v = f.valuation()
            try:
                R = _substitution_map(guess(f.list()[v:], OA, order=d), -v)
                if 0<R.order()<r and dop%R==0: return R
            except ValueError: pass
        else:
            der = [ f.truncate() ]
            for k in range(d): der.append( der[-1].derivative() )
            mat = matrix(d + 1, 1, der)
            if verbose: print("Try guessing annihilator with HP approximants")
            min_basis = mat.minimal_approximant_basis(order)
            rdeg = min_basis.row_degrees()
            if max(rdeg) > 1 + min(rdeg):
                i0 = min(range(len(rdeg)), key=lambda i: rdeg[i])
                R, g = PlainDifferentialOperator(dop).extend_scalars(K.gen())
                R = R.parent()(list(min_basis[i0]))
                if dop%R==0: return R

    if order>r*(bound + 1) and verbose:
        print("Ball Hermite--Padé approximants not implemented yet")

    return "Inconclusive"


################################################################################
### Tools ######################################################################
################################################################################

def _try_rational(dop):

    r"""
    Return a first order right-hand factor of ``dop`` as soon as it has rational
    solutions.

    INPUT:
     -- ``dop`` -- differential operator

    OUTPUT:
     -- ``right_factor`` -- differential operator, or ``None``

    EXAMPLES::

        sage: from ore_algebra.analytic.factorization import _try_rational
        sage: from ore_algebra.examples import ssw
        sage: dop = ssw.dop[1,0,0]; dop
        (16*t^4 - t^2)*Dt^3 + (144*t^3 - 9*t)*Dt^2 + (288*t^2 - 15)*Dt + 96*t
        sage: _try_rational(dop)
        t*Dt + 2

    """

    for (f,) in dop.rational_solutions():
        d = f.gcd(f.derivative())
        right_factor = (1/d)*(f*dop.parent().gen() - f.derivative())
        return right_factor

    return None

def _reduced_row_echelon_form(mat):
    R, p = row_echelon_form(mat, pivots=True)
    rows = list(R)
    for j in p.keys():
        for i in range(p[j]):
            rows[i] = rows[i] - rows[i][j]*rows[p[j]]
    return matrix(rows)

def _local_exponents(dop, multiplicities=True):
    ind_pol = dop.indicial_polynomial(dop.base_ring().gen())
    return ind_pol.roots(QQbar, multiplicities=multiplicities)

def _largest_modulus_of_exponents(dop):

    z = dop.base_ring().gen()
    dop = PlainDifferentialOperator(dop)
    lc = dop.leading_coefficient()//gcd(dop.list())

    out = 0
    for pol, _ in list(lc.factor()) + [ (1/z, None) ]:
        local_exponents = dop.indicial_polynomial(pol).roots(QQbar, multiplicities=False)
        local_largest_modulus = max([x.abs().ceil() for x in local_exponents], default=QQbar.zero())
        out = max(local_largest_modulus, out)

    return out

def _degree_bound_for_right_factor(dop):

    r = dop.order() - 1
    #S = len(dop.desingularize().leading_coefficient().roots(QQbar)) # too slow (example: QPP)
    S = len(PlainDifferentialOperator(dop).leading_coefficient().roots(QQbar))
    E = _largest_modulus_of_exponents(dop)
    bound = r**2*(S + 1)*E + r*S + r**2*(r - 1)*(S - 1)/2

    return ZZ(bound)

def _random_combination(mono):
    prec, C = customized_accuracy(mono), mono[0].base_ring()
    if prec<10: raise PrecisionError
    ran = lambda : C(QQ.random_element(prec), QQ.random_element(prec))
    return sum(ran()*mat for mat in mono)


myadjoint = lambda dop: sum((-dop.parent().gen())**i*pi for i, pi in enumerate(dop.list()))

def _diffop_companion_matrix(dop):
    r = dop.order()
    A = block_matrix([[matrix(r - 1 , 1, [0]*(r - 1)), identity_matrix(r - 1)],\
                      [ -matrix([[-dop.list()[0]]]) ,\
                        -matrix(1, r - 1, dop.list()[1:-1] )]], subdivide=False)
    return A

def _transition_matrix_for_adjoint(dop):

    """
    Return an invertible constant matrix Q such that: if M is the monodromy of
    dop along a loop gamma, then the monodromy of the adjoint of dop along
    gamma^{-1} is equal to Q*M.transpose()*(~Q), where the monodromies are
    computed in the basis given by .local_basis_expansions method.

    Assumptions: dop is monic, 0 is the base point, and 0 is not singular.
    """

    AT = _diffop_companion_matrix(dop).transpose()
    r = dop.order()
    B = [identity_matrix(dop.base_ring(), r)]
    for k in range(1, r):
        Bk = B[k - 1].derivative() - B[k - 1] * AT
        B.append(Bk)
    P = matrix([ B[k][-1] for k in range(r) ])
    Delta = diagonal_matrix(QQ, [1/factorial(i) for i in range(r)])
    Q = Delta * P(0) * Delta
    return Q


def _guess_symbolic_coefficients(vec, alg_degree, verbose=False):

    """
    Return a reasonable symbolic vector contained in the ball vector ``vec``
    and its field of coefficients if something reasonable is found, or
    ``NothingFound`` otherwise.

    INPUT:
     -- ``vec``          -- ball vector
     -- ``alg_degree``   -- positive integer

    OUTPUT:
     -- ``symb_vec`` -- vector with exact coefficients, or ``NothingFound``
     -- ``K``        -- QQ, or a number field, or None (if ``symb_vec``=``NothingFound``)


    EXAMPLES::

        sage: from ore_algebra.analytic.factorization import _guess_symbolic_coefficients
        sage: C = ComplexBallField(); err = C(0).add_error(RR.one()>>40)
        sage: vec = vector(C, [C(sqrt(2)) + err, 3 + err])
        sage: _guess_symbolic_coefficients(vec, 1)
        ('NothingFound', None)
        sage: _guess_symbolic_coefficients(vec, 2)
        ([a, 3],
         Number Field in a with defining polynomial y^2 - 2 with a = 1.414213562373095?)

    """


    if verbose: print("Try guessing symbolic coefficients")

    # fast attempt that working well if rational
    v1, v2 = [], []
    for x in vec:
        if not x.imag().contains_zero(): break
        x, err = x.real().mid(), x.rad()
        err1, err2 = err, 2*err/3
        v1.append(x.nearby_rational(max_error=x.parent()(err1)))
        v2.append(x.nearby_rational(max_error=x.parent()(err2)))
    if len(v1)==len(vec) and v1==v2:
        if verbose: print("Find rational coefficients")
        return v1, QQ

    p = customized_accuracy(vec)
    if p<30: return "NothingFound", None
    for d in range(2, alg_degree + 1):
        v1, v2 = [], []
        for x in vec:
            v1.append(algdep(x.mid(), degree=d, known_bits=p-10))
            v2.append(algdep(x.mid(), degree=d, known_bits=p-20))
        if v1==v2:
            symb_vec = []
            for i, x in enumerate(vec):
                roots = v1[i].roots(QQbar, multiplicities=False)
                k = len(roots)
                i = min(range(k), key = lambda i: abs(roots[i] - x.mid()))
                symb_vec.append(roots[i])
            K, symb_vec = as_embedded_number_field_elements(symb_vec)
            if not all(symb_vec[i] in x for i, x in enumerate(vec)): return "NothingFound", None
            if verbose: print("Find algebraic coefficients in a number field of degree", K.degree())
            return symb_vec, K

    return "NothingFound", None

_frobenius_norm = lambda m: sum([x.abs().mid()**2 for x in m.list()]).sqrt()

def _formal_finite_sum_to_power_series(f, PSR):

    """ Assumtion: x is extended at 0 (you have to shift otherwise). """

    if isinstance(f, list):
        return [ _formal_finite_sum_to_power_series(g, PSR) for g in f ]

    out = PSR.zero()
    for constant, monomial in f:
        if constant!=0:
            out += constant*PSR.gen()**monomial.n

    return out

def _euler_representation(dop):

    r"""
    Return the list of the coefficients of dop with respect to the powers of
    z*Dz.
    """

    z, n = dop.base_ring().gen(), dop.order()
    output = [ dop[0] ] + [0]*n
    l = [0] # coefficients of T(T-1)...(T-k+1) (initial: k=0)

    for k in range(1, n+1):

        newl = [0]
        for i in range(1, len(l)):
            newl.append((-k+1)*l[i]+l[i-1])
        l = newl + [1]

        ck = dop[k]
        for j in range(1, k+1):
            output[j] += ck*z**(-k)*l[j]

    return output

def _substitution_map(dop, e):

    r"""
    Return the operator obtained from ``dop`` after the substitution map
    T --> T + e, where T = z*Dz denotes Euler operator.

    Note: this corresponds to multiply the solution space by z^(-e).

    EXAMPLES::

        sage: from ore_algebra.analytic.factorization import _substitution_map
        sage: from ore_algebra.examples import ssw
        sage: dop = ssw.dop[1,0,0]; dop
        (16*t^4 - t^2)*Dt^3 + (144*t^3 - 9*t)*Dt^2 + (288*t^2 - 15)*Dt + 96*t
        sage: f = dop.power_series_solutions(20)[0]
        sage: dop(f)
        O(t^18)
        sage: dop = _substitution_map(dop,-3)
        sage: dop(f.parent().gen()^3*f)
        O(t^21)

    """

    l = _euler_representation(PlainDifferentialOperator(dop))
    for i, c in enumerate(l):
        for k in range(i):
            l[k] += binomial(i, k)*e**(i - k)*c
    T = dop.base_ring().gen()*dop.parent().gen()
    output = sum(c*T**i for i, c in enumerate(l))

    return output
