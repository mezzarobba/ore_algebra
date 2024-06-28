# vim: tw=80
r"""
Stokes matrices

This implementation is based on connection-to-Stokes formulas à la
Loday-Richaud--Remy. It is currently limited to singular points of pure level
one. It is also possible to compute Stokes matrices using Borel-Laplace
summation (see :mod:`ore_algebra.analytic.borel_laplace`), but the present code
should usually be faster.


EXAMPLES::

    sage: from ore_algebra import OreAlgebra
    sage: Pol.<x> = QQ[]
    sage: Dop.<Dx> = OreAlgebra(Pol, 'Dx')

    sage: from ore_algebra.analytic.stokes import stokes_matrices, stokes_dict
    sage: DD = x^2*Dx

Example from §2 of (Fauvet, Richard-Jung, Thomann, 2009). Here our basis is the
one used in the article, and the computed Stokes matrices agree with the results
given in §3.3, (2)::

    sage: dop = (x^4 + 2*x^5)*Dx^2 + (8*x^4-x^3)*Dx + (4*x^3-2*x^2-3*x-1)
    sage: stokes = stokes_dict(dop)
    sage: stokes.keys()
    dict_keys([1, -1])
    sage: stokes[1]
    [                1.000000000000...                  0]
    [[+/- ...] + [-0.99404246871...]*I  1.000000000000...]
    sage: stokes[-1]
    [ 1.000000000000...  [+/- ...] + [-72.363839794...]*I]
    [                 0                 1.000000000000...]

Same article, §3.3, (3)::

    sage: dop = (x^4 + 2*x^5)*Dx^2 + (12*x^4+x^3)*Dx + (12*x^3-3*x^2-x-1)
    sage: stokes = stokes_dict(dop, RBF(1e-15))
    sage: stokes[1]
    [                1.000000000000...                      0]
    [[+/- ...] + [-0.21707530830...]*I      1.000000000000...]
    sage: stokes[-1]
    [  1.000000000000... [+/- ...] + [85.92634932...]*I]
    [                  0              1.000000000000...]

Bessel equation (same article, §3.3, (4)). Our basis puts `e^{i/x}` first
(decreasing imaginary parts), and hence is in the reverse order compared theirs::

    sage: dop = (x^2*Dx^2 + x*Dx + (x^2-1/16)).annihilator_of_composition(1/x)
    sage: stokes = stokes_dict(dop, RBF(1e-15))
    sage: stokes.keys()
    dict_keys([-1*I, 1*I])
    sage: stokes[I]
    [                  1.000000000000...                        0]
    [[+/- ...] + [-1.4142135623730...]*I        1.000000000000...]
    sage: stokes[-I]
    [       1.000000000000... [+/- ...] + [-1.4142135623730...]*I]
    [                       0                   1.000000000000...]

Example from §4.2 of the same article::

    sage: dop = ((-4*x^5 + 6*x^6 - 2*x^7)*Dx^3
    ....:       + (27*x^5 - 2*x^4 - 8*x^3 - 11*x^6)*Dx^2
    ....:       + (-11*x^5 - 4*x + 9*x^3 + 28*x^4 + 4*x^2)*Dx
    ....:       + (4 - x^4 - 4*x + 7*x^2 + 4*x^3))
    sage: dop.generalized_series_solutions()
    [exp(x^(-1))*x^(1/2)*(1 + x + x^2 + x^3 + x^4 + O(x^5)),
     exp(x^(-1))*(1 + x + x^2 + x^3 + x^4 + O(x^5)),
     x*(1 + 2*x^2 - 4*x^3 + 20*x^4 + O(x^5))]
    sage: stokes = stokes_dict(dop, RBF(1e-30))
    sage: (stokes[1] - 1).norm() < 1e-25
    True
    sage: stokes[-1]
    [  1.000...        0 [+/- ...] + [6.2831853071795864769252867...]*I]
    [       0   1.000...                        [+/- ...] + [+/- ...]*I]
    [       0          0                                       1.000...]

TESTS:

Hypergeometric functions::

    sage: def hgeom(mu, nu1, nu2):
    ....:     return -DD^2 + (1 + (nu1 + nu2 - 1)*x)*DD - (mu*x + (nu1 - 1)*(nu2 - 1)*x^2)
    sage: def hgeom_ref(mu, nu1, nu2):
    ....:     return matrix(CBF, 2, 2, [1, 0, -2*I*pi/gamma(1+mu-nu1)/gamma(1+mu-nu2), 1])
    sage: def hgeom_check(mu, nu1, nu2, eps=1e-13):
    ....:     stokes = stokes_dict(hgeom(mu, nu1, nu2))
    ....:     assert list(sorted(stokes.keys())) == [-1, 1]
    ....:     delta = stokes[1] - hgeom_ref(mu, nu1, nu2)
    ....:     assert all(c.contains_zero() for c in delta.list())
    ....:     assert all(c.diameter() < eps for c in delta.list())
    sage: hgeom_check(1, 1, 3/2)
    sage: hgeom_check(1, 1/3, 3/2)
    sage: hgeom_check(1, 4/3, 5/3)

A case where the exponents do not lie in the right half-plane::

    sage: hgeom_check(1, 1/2, 1/2)

Operators with coefficients (and exponents) in a number field::

    sage: hgeom_check(1, I, I, 1e-12)
    sage: K.<cbrt2> = NumberField(x^3 - 2, embedding=2.^(1/3))
    sage: hgeom_check(1, cbrt2, cbrt2-1, 1e-12)  # long time (1.8 s)

Richard-Jung (2011), §5::

    sage: dop = (x^3*Dx^2 - 1).annihilator_of_composition(x^2)
    sage: dop.generalized_series_solutions()
    [exp(2*x^(-1))*x^(3/2)*(1 - 3/16*x - 15/512*x^2 - 105/8192*x^3 - 4725/524288*x^4 + O(x^5)),
     exp(-2*x^(-1))*x^(3/2)*(1 + 3/16*x - 15/512*x^2 + 105/8192*x^3 - 4725/524288*x^4 + O(x^5))]
    sage: stokes_dict(dop)[1]
    [                          1.000...         0]
    [[+/- ...] + [2.0000000000000...]*I  1.000...]

An example with three aligned Stokes values (result checked by comparing with
Borel-Laplace summation) where and exact calculation should be possible(?)::

    sage: dop = 2*DD^3+(x-5)*DD^2+(2*x+2)*DD-2*x
    sage: stokes = stokes_dict(dop)
    sage: stokes[1]
    [                  1.000000000000...                                   0                  0]
    [[+/- ...] + [-4.4562280437884...]*I                   1.000000000000...                  0]
    [ [4.8367983046245...] + [+/- ...]*I  [+/- ...] + [2.1708037636748...]*I  1.000000000000...]
    sage: norm(stokes[-1] - 1) < 1e-10
    True

A fourth-order example::

    sage: dop = (x^8*(10*x^4+180*x^3+495*x^2-3888)*Dx^4
    ....:        +1/4*x^6*(170*x^5+3540*x^4+8055*x^3-11880*x^2-128304*x+93312)*Dx^3
    ....:        +1/9*x^4*(245*x^6+6525*x^5+22635*x^4-18225*x^3-413667*x^2+664848*x-384912)*Dx^2
    ....:        +1/36*x^2*(20*x^7-880*x^6-3780*x^5-94320*x^4-471987*x^3+95256*x^2-104976*x+839808)*Dx
    ....:        +2/9*x*(200*x^6+1440*x^5+11790*x^4+35640*x^3+23085*x^2-104976))
    sage: stokes = stokes_dict(dop, RBF(1e-30))
    sage: stokes.keys()
    dict_keys([1, -1])
    sage: stokes[1][2,0]
    [+/- ...] + [-2.060897024589991165631724347...]*I
    sage: stokes[1][3,1]
    [+/- ...] + [-1.7320508075688772935274463415...]*I

We double-check the above results using Borel-Laplace summation::

    sage: import ore_algebra.analytic.borel_laplace as bl
    sage: x0 = 1/10; dtheta = pi/16
    sage: mat_left = bl.fundamental_matrix(dop, x0, dtheta, RBF(1e-40))    # not tested (90 s)
    sage: mat_right = bl.fundamental_matrix(dop, x0, -dtheta, RBF(1e-40))  # not tested (85 s)
    sage: (stokes[1] - ~mat_left*mat_right).norm() < 1e-9                  # not tested
    True

::

    sage: dop1 = dop.annihilator_of_composition(-x)
    sage: mat_left = bl.fundamental_matrix(dop1, x0, pi/16, RBF(1e-40))    # not tested (85 s)
    sage: mat_right = bl.fundamental_matrix(dop1, x0, -pi/16, RBF(1e-40))  # not tested (83 s)

The matrix `stokes[-1]` is expressed in the basis
`f_1 = e^{-1/x} x + \cdots,
 f_2 = e^{-2/x} x^{3/4} + \cdots,
 f_3 = e^{-3/x} x + \cdots`,
while the change of variables `z = -x` leads to a Stokes matrix naturally
expressed in the basis
`e^{3/z} z = -f_3,
 e^{2/z} z^{3/4} = (-1)^{3/4} f_2,
 e^{1/z} z = -f_1`. ::

    sage: P = matrix(QQbar, 4)
    sage: P[0,3] = P[2,1] = P[3,0] = -1; P[1,2] = QQbar(-1)^(3/4)
    sage: norm(stokes[-1] - ~P*~mat_left*mat_right*P) < 1e-12              # not tested
    True

A decomposable operator::

    sage: dop1 = -DD^2 + (3*x/2+2)*DD - 2*x
    sage: dop2 = -DD^2 + (4 + 2*x)*DD + (-3-4*x-2/9*x^2)
    sage: stokes1 = stokes_dict(dop1)
    sage: stokes2 = stokes_dict(dop2)
    sage: stokes12 = stokes_dict(dop1.lclm(dop2))
    sage: for omega, mat in stokes12.items():
    ....:     assert all(mat[i,j].contains_zero()
    ....:                for i in range(4) for j in range(4)
    ....:                if i != j and {i, j} not in [{0,2}, {1,3}])
    ....:     assert mat[0,2].overlaps(stokes1[omega][0,1])
    ....:     assert mat[2,0].overlaps(stokes1[omega][1,0])
    ....:     assert mat[1,3].overlaps(stokes2[omega][0,1])
    ....:     assert mat[3,1].overlaps(stokes2[omega][1,0])
"""

import itertools
import logging

from sage.graphs.generators.basic import CompleteGraph
from sage.matrix.constructor import matrix
from sage.matrix.special import block_matrix, identity_matrix
from sage.misc.converting_dict import KeyConvertingDict
from sage.rings.all import CC, QQbar
from sage.rings.complex_arb import ComplexBallField
from sage.rings.imaginary_unit import I
from sage.rings.real_arb import RBF
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

from . import polynomial_root
from . import utilities

from .borel_laplace import BorelIniMap, IniMap
from .differential_operator import DifferentialOperator
from .geometry import in_triangle, orient2d_interval
from .monodromy import formal_monodromy
from .path import PathPrecisionError, Point

logger = logging.getLogger(__name__)


def connection_to_stokes_coefficients(expo, order, ring):
    r"""
    Compute the coefficients

    .. MATH::

        \frac{1}{j!} \frac{\mathrm d^j}{\mathrm d\lambda^j} \frac{e^{- i \pi (\lambda + 1)}}{\Gamma(-\lambda)}

    evaluated at `\lambda` = ``expo``, for `j` from 0 to ``order-1``.

    These coefficients appear in the expression of Stokes multipliers in terms
    of the connection coefficients between singular points in the Borel plane
    (e.g., Remy 2007, Lemma 2.29).

    EXAMPLES::

        sage: from ore_algebra.analytic.stokes import connection_to_stokes_coefficients
        sage: connection_to_stokes_coefficients(0, 3, CBF)
        [0,
        1.0000000000000...,
        [-0.57721566490153...] + [-3.1415926535897...]*I]
        sage: connection_to_stokes_coefficients(4, 3, CBF)
        [0,
        [24.000000000000...] + [+/- ...]*I,
        [36.146824042363...] + [-75.398223686155...]*I]
        sage: connection_to_stokes_coefficients(-1, 3, CBF)
        [[1.0000000000000...] + [+/- ...]*I,
        [-0.5772156649015...] + [-3.1415926535897...]*I,
        [-5.5906802720649...] + [1.8133764923916...]*I]
        sage: connection_to_stokes_coefficients(QQbar.zeta(3), 3, CBF)
        [[-19.08060508718...] + [-14.00966549355...]*I,
        [-61.7281620549...] + [92.6676427956...]*I,
        [215.841468281...] + [148.348871486...]*I]
    """
    eps = PolynomialRing(ring, 'eps').gen()
    pii = ring.pi()*I
    f = -(-pii*(expo + eps))._exp_series(order)
    g = (- expo - eps)._rgamma_series(order)
    res = f.multiplication_trunc(g, order)
    return res.padded_list(order)


class ConnectionToStokesIniMap(IniMap):

    max_shift = -1

    def compute_coefficient(self, sol1, ser, offset):
        # See, e.g., Remy2007, lemme 2.29
        if offset + sol1.shift - 1 < 0:
            return self.ring.zero()
        coeff = ser[offset + sol1.shift - 1]
        # XXX redundant computations when log_power > 0
        csts = connection_to_stokes_coefficients(
            sol1.valuation_as_ball(self.ring) - 1,
            len(coeff) - sol1.log_power,
            self.ring)
        twopii = 2*self.ring.pi()*I
        return twopii*sum(c*a for c, a in zip(csts, coeff[sol1.log_power:]))


class _sort_key_chords:

    def __init__(self, value):
        self.theta, self.s0, self.s1 = value

    def stage2_key(self):
        # Since -π < θ ≤ 0, sorting on (-Im(s0), Re(s0)) is equivalent to
        # sorting in the direction θ (computationally, not quite).
        # XXX Consider using the new sort_keys from PolynomialRoot here too.
        s0 = self.s0.interval().center()
        s1 = self.s1.interval().center()
        return(-s0.imag(), s0.real(), id(self.s0),
               -s1.imag(), s1.real(), id(self.s1))

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        if self.theta < other.theta:
            return True
        elif self.theta > other.theta:
            return False
        return self.stage2_key() < other.stage2_key()


def _singular_directions(sing, ini_prec=53):
    r"""
    Detect aligned singularities, sort alignments by direction

    TESTS::

        sage: from ore_algebra import OreAlgebra
        sage: Pol.<x> = QQ[]
        sage: Dop.<Dx> = OreAlgebra(Pol)

        sage: from ore_algebra.analytic.differential_operator import DifferentialOperator
        sage: from ore_algebra.analytic.stokes import _singular_directions
        sage: _singular_directions(DifferentialOperator(x*(x-1)*(x-2)*Dx - x)._singularities())
        [[1, [0, 1, 2]], [-1, [2, 1, 0]]]
        sage: _singular_directions(DifferentialOperator(x*(x^2+1)*Dx - x)._singularities())
        [[-1*I, [1*I, 0, -1*I]], [1*I, [-1*I, 0, 1*I]]]
        sage: sd = _singular_directions(DifferentialOperator(x*(x-1)*(x^2+2)*Dx - x)._singularities())
        sage: [[CC(alpha).arg(), *data] for alpha, *data in sd[:(len(sd)+1)//2]]
        [[-2.186276..., [1, -1.414213562373095?*I]],
        [-1.5707963..., [1.414213562373095?*I, 0, -1.414213562373095?*I]],
        [-0.9553166..., [1.414213562373095?*I, 1]],
        [0.00000000..., [0, 1]]]
        sage: arctan(sqrt(2)).n(), (pi - arctan(sqrt(2))).n()
        (0.9553166..., 2.18627...)
    """
    IC = ComplexBallField(ini_prec)
    pi = IC.base().pi()

    # Compute the list of pairs (s0, s1) s.t. -π < arg(s1-s0) ≤ 0
    chords = []
    for s0, s1 in itertools.combinations(sing, 2):
        theta = (IC(s1) - IC(s0)).arg()
        if theta.overlaps(pi):
            # Recompute theta to avoid looping on [-π,π]
            theta, s0, s1 = (IC(s0) - IC(s1)).arg(), s1, s0
        if theta.contains_zero() and not theta.is_zero():
            # Ensure arguments equal to zero are exact (needed for handling
            # branch cuts)
            if s0.cmp_imag(s1) == 0:
                theta = theta.parent().zero()
            else:
                return _singular_directions(sing, 2*ini_prec)
        elif theta > 0:
            theta, s0, s1 = theta - pi, s1, s0
        chords.append((theta, s0, s1))
    # Sort by argument, ensuring that, in each direction, pairs with the same s0
    # come next to each other (ordered in the direction theta, but this is not
    # guaranteed at this stage)
    chords.sort(key=_sort_key_chords)

    dirs = []
    cur_theta = cur_dir = None
    for theta, s0, s1 in chords:
        dir = s1.as_algebraic() - s0.as_algebraic()
        if cur_theta is None or not theta.overlaps(cur_theta):
            # new direction
            align = [s0, s1]
            dirs.append([dir/abs(dir), align])
            align_map = {s0: align, s1: align}
            cur_theta, cur_dir = theta, dir
        else:
            ratio = dir/cur_dir
            cur_align = dirs[-1][-1]
            if s0 is cur_align[0] and ratio.imag().is_zero() and ratio > 1:
                # new point in the current align_map
                cur_align.append(s1)
                align_map[s1] = cur_align
            elif align_map.get(s0) is align_map.get(s1) is not None:
                # redundant pair
                pass
            elif ratio.imag().is_zero() and ratio > 0:
                # new align_map in the same direction
                align = align_map[s0] = align_map[s1] = [s0, s1]
                dirs[-1].append(align)
            else:
                # our ordering may be incorrect, increase the working precision
                return _singular_directions(sing, 2*ini_prec)

    opp = [[-dir, *(list(reversed(align)) for align in alignments)]
           for dir, *alignments in dirs]

    return dirs + opp


class Triangle(frozenset):

    def __init__(self, elements, *, flat=False):
        # initialization of the frozenset elements is handled by __new__
        assert len(elements) == 3
        self.flat = flat # ignored by comparisons/hashing

    def __repr__(self):
        from sage.all import ComplexField
        C = ComplexField(10)
        return ("{" + ", ".join(str(C(a)) for a in self)
                + (" (flat)" if self.flat else "") + "}")


class TriangleQueue:

    def __init__(self, triangles):
        # triangles[i] = triangles with i known edges
        # We use dicts with value == key because sets offer no way (afaict) to
        # retrieve the actual element contained in the set given a key that
        # compares equal to it.
        self.triangles = [{t: t for t in triangles}, {}, {}]

    def __repr__(self):
        return repr([set(d.values()) for d in self.triangles])

    def pop(self):
        # XXX consider keeping track of the accuracies and returning the best
        # triangle
        _, t = self.triangles[2].popitem()
        return t

    def inc(self, k):
        for i in [0, 1, 2]:
            t = self.triangles[i].pop(k, None)
            if t is None:
                continue
            if i < 2:
                self.triangles[i + 1][t] = t
                # logger.debug("%s now has %s known edges", t, i + 1)
            break

    def inc_all(self, a, b, verts):
        for c in verts:
            if c is a or c is b:
                continue
            self.inc(Triangle((a, b, c)))


def interval_triangle_is_empty(sing, a, b, c):
    aa, bb, cc = a.interval(), b.interval(), c.interval()
    for z in sing:
        if z is a or z is b or z is c:
            continue
        try:
            if in_triangle(orient2d_interval, aa, bb, cc, z.interval()):
                return False
        except ValueError:
            return False
    return True


class SingConnectionDict(dict):

    def __init__(self, dop, IC):
        self.dop = dop
        self.IC = IC

    def _decompose_missing_edge(self, t):
        r"""
        Sort the vertices of t as a, b, c so that ab and bc are known while ac
        is not.
        """
        a, b, c = t
        if (a, b) in self:
            if (b, c) in self:
                assert (a, c) not in self
                return a, b, c
            else:
                assert (a, c) in self and (c, b) not in self
                return c, a, b
        else:
            assert (b, c) in self and (a, c) in self
            return b, c, a

    def _combine_edges(self, a, b, c, flat):
        r"""
        Compute the transition matrix along ac from those along ab and bc.
        """
        # If the vertex m ∈ {a, b, c} that lies vertically in the middle is
        # located to the right of the opposite edge oriented from bottom to top,
        # then one of the paths a → c and a → b → c crosses the branch cut at m
        # while the other does not, and we need to correct for the local
        # monodromy. In the presence of vertices with the same y-coordinate, the
        # one to the right is considered infinitesimally lower for this purpose,
        # because of branch cuts are sticky on their top side.
        #
        # When b lies on the segment [ac], the transition matrix associated to
        # ac in our context corresponds to a path passing to the right of b.
        # Thus, for flat triangles, we regard m (which then coincides with the
        # vertex joining the two short edges) as lying to the right of the long
        # edge (=> monodromy correction) iff the long edge is oriented from top
        # to bottom by the path using it (that is, using the extended vertical
        # ordering of the previous paragraph, iff c < m =  b < a or
        # c < m = a < b or b < m = c < a, though, in practice, only the first of
        # these three cases should be useful).

        # XXX for flat triangles, we already have this information via the
        # associated argument in alignments and could maybe avoid recomputing it.
        vsort = sorted([a, b, c],
                       key=polynomial_root.sort_key_bottom_to_top_with_cuts)
        if flat:
            assert vsort[1] is b, ("trying to compute a short edge of a flat "
                                   "triangle using the long edge")
        # We only call orient2d on nondegenerate triangles. Except in extreme
        # cases, it should succeed without triggering exactification even if our
        # intervals for a, b, c are too wide.
        if (flat and vsort[0] is c) or polynomial_root.orient2d(*vsort) > 0:
            vert_with_cut = vsort[1]
            delta = formal_monodromy(self.dop, vert_with_cut, self.IC)
            # The correction one needs depends how the edge ac orients the
            # triangle. This is not the same orientation condition as above!
            orient = +1 if flat else -polynomial_root.orient2d(a, b, c)
            delta = delta**orient
        else:
            vert_with_cut = None

        mat_ac = identity_matrix(self.IC, self.dop.order())
        if vert_with_cut is a:
            mat_ac = delta*mat_ac
        mat_ac = self[a, b]*mat_ac
        if vert_with_cut is b:
            mat_ac = delta*mat_ac
        mat_ac = self[b, c]*mat_ac
        if vert_with_cut is c:
            mat_ac = delta*mat_ac

        accu_ab = _matrix_accuracy(self[a, b])
        accu_bc = _matrix_accuracy(self[b, c])
        accu_ac = _matrix_accuracy(mat_ac)
        # accu_delta = _matrix_accuracy(delta) if vert_with_cut
        logger.debug("%s -> %s: via %s, accuracies: (%s, %s) -> %s", a, c, b,
                     accu_ab, accu_bc, accu_ac)

        return mat_ac

    def _close_triangle(self, t):
        a, b, c = self._decompose_missing_edge(t)
        # logger.debug("closing triangle %s", t)
        mat_ac = self._combine_edges(a, b, c, t.flat)
        if t.flat:
            # In this case, the transition matrices a → c and c → a are not
            # inverse of each other!
            mat_ca = self._combine_edges(c, b, a, t.flat)
        else:
            # XXX call _combine_edges again (maybe sharing some work) to avoid
            # losing too much accuracy?
            mat_ca = ~mat_ac
        return a, c, mat_ac, mat_ca

    def _transition_matrices_along_spanning_tree(self, sing):
        # This computes the connection matrices with the usual oaa conventions
        # (i.e., without the local adjustments that may be required for the
        # connection-to-Stokes formulas to apply in the form stated by LRR)

        eps = RBF.one() >> self.IC.precision() + 4

        def dist(e):
            i, j, _ = e
            return abs(CC(sing[i]) - CC(sing[j]))

        # Sage graphs require vertices to be <-comparable, so we use indices
        complete_graph = CompleteGraph(len(sing))
        spanning_tree = complete_graph.min_spanning_tree(dist)

        # XXX we should actually compute all edges from a given vertex at
        # once... and use the same tricks as in monodromy_matrices
        for i, j, _ in spanning_tree:
            a = sing[i].as_exact()
            b = sing[j].as_exact()
            logger.debug("%s -> %s: direct summation", a, b)
            mat = self.dop.numerical_transition_matrix([a, b], eps)
            yield sing[i], sing[j], mat

    def fill(self, sing, sing_dirs):

        nsing = len(sing)

        logger.debug("sing = %s", sing)

        # XXX This is O(n⁴)! Better way to propagate the transition matrices?
        # (1) Closed triangles that we can check to contain no other singular
        # points using interval tests only. We might miss some empty triangles,
        # but it only matters if that prevents us from reaching some edges, and
        # we will check that in due time.
        triangles = [
            Triangle((sing[p], sing[q], sing[r]))
            for p in range(nsing)
            for q in range(p + 1, nsing)
            for r in range(q + 1, nsing)
            if interval_triangle_is_empty(sing, sing[p], sing[q], sing[r])]
        # (2) Pairs of non-consecutive singular points on a line, each completed
        # by an intermediate point. There may some overlap with (1). In that
        # case, TriangleQueue will only keep the last copy (=> the one with the
        # flat flag set).
        triangles.extend([
            Triangle([align[i], align[i+1], align[j]], flat=True)
                     for _, *alignments in sing_dirs
                     for align in alignments
                     for i in range(len(align) - 2)
                     for j in range(i+2, len(align))])
        triangles = TriangleQueue(triangles)

        spine = self._transition_matrices_along_spanning_tree(sing)

        for edge_count in itertools.count(1):
            # logger.debug("triangles=%s", triangles)
            # Attempt to compute one more transition matrix by combining
            # known ones. If this is not possible, compute one from scratch.
            #
            # (Note: in the future, we may want to yield the newly computed
            # matrix at each iteration. This may be useful in algorithms like
            # the symbolic-numeric factorization algorithm.)
            try:
                a1, b1, mat_ab, mat_ba = self._close_triangle(triangles.pop())
            except KeyError:
                try:
                    a1, b1, mat_ab = next(spine)
                    # XXX implicitly computes inverses of inverses
                    mat_ba = ~mat_ab
                except StopIteration:
                    if edge_count < nsing*(nsing-1)//2:
                        raise PathPrecisionError("missed some edges")
                    break
            assert (a1, b1) not in self
            assert (b1, a1) not in self
            self[a1, b1] = mat_ab
            self[b1, a1] = mat_ba
            triangles.inc_all(a1, b1, sing)

        return self


def _newton_polygon(dop):
    r"""
    Newton polygon with weight(d/dx) = -1
    """
    x = dop.base_ring().gen()
    return [[max(slope-1, 0), pol] for slope, pol in dop.newton_polygon(x)]


def _bdop_singularities(bdop, dop, npol):
    sing = bdop._singularities(multiplicities=True)
    assert sum(m for _, m in sing) == dop.order()
    assert all(edge_pol(s.interval()).contains_zero()
               for level, edge_pol in npol if level != 0
               for s, m in sing if not s.is_zero())
    return [s for s, _ in sing]


def stokes_matrices(dop, eps=1e-15):
    r"""
    Stokes matrices of ``dop`` at the origin.

    INPUT:

    - ``dop`` - differential operator of pure level one at 0 (i.e., all
      exponential parts must be of the form `e^{α/x}` for some `α`)
    - ``eps`` - tolerance parameter

    OUTPUT:

    This method is a generator. It produces the pairs `(e^{iω}, M)` where `ω`
    is a singular direction and `M` is the corresponding Stokes matrix.

    See :func:`stokes_matrices` for more information on the conventions used to
    define the Stokes matrices.

    EXAMPLES::

        sage: from ore_algebra import OreAlgebra
        sage: Pol.<x> = QQ[]
        sage: Dop.<Dx> = OreAlgebra(Pol, 'Dx')

        sage: from ore_algebra.analytic.stokes import stokes_matrices

        sage: dop = x^3*Dx^2 + x*(x+1)*Dx - 1
        sage: stokes = dict(stokes_matrices(dop))
        sage: stokes.keys()
        dict_keys([1, -1])
        sage: stokes[QQbar(-1)]
        [ 1.000000000000... [+/- ...] + [6.2831853071795...]*I]
        [                 0                  1.000000000000...]
    """
    Dop, Pol, Csts, dop = dop._normalize_base_ring()
    eps = RBF(eps)
    Dx = Dop.gen()
    x = Pol.gen()
    IC = ComplexBallField(utilities.prec_from_eps(eps))
    if not IC.has_coerce_map_from(Csts):
        raise ValueError(f"unsupported base ring {Csts}")

    npol = _newton_polygon(dop)
    bad_levels = [level for level, _ in npol
                        if level not in [0, 1]]
    if bad_levels:
        raise NotImplementedError(
            f"levels {bad_levels} ≠ 0, 1 are not supported")

    bdop = DifferentialOperator(dop.borel_transform())
    sing = _bdop_singularities(bdop, dop, npol)

    dirs = _singular_directions(sing)
    tmat = SingConnectionDict(bdop, IC).fill(sing, dirs)

    # The transition matrix s0 → s1 contributes to the columns of the Stokes
    # matrix in the singular direction [s0, s1) corresponding to solutions
    # with exponential part associated to s0.

    # We want to sort the rows/columns of the Stokes matrix by decreasing
    # asymptotic dominance. As each block corresponds to a factor exp(-s/x),
    # this corresponds to sorting sing by increasing real part.
    sing.sort(key=polynomial_root.sort_key_left_to_right_real_last) # XXX earlier?

    borel_mat = {}; c2s_mat = {}
    for s in sing:
        tdop  = dop.symmetric_product(x**2*Dx + s.as_number_field_element())
        # sbdop = tdop.borel_transform()
        sbdop = bdop.shift(Point(s, bdop))
        borel_mat[s] = BorelIniMap(tdop, sbdop, IC).run()
        c2s_mat[s] = ConnectionToStokesIniMap(sbdop, tdop, IC).run()

    for dir, *alignments in dirs:
        stokes_block = {(s0, s1): matrix(IC, c2s_mat[s1].nrows(),
                                             borel_mat[s0].ncols())
                        for s0 in sing for s1 in sing}
        for align in alignments:
            for s0, s1 in itertools.combinations(align, 2):
                # The connection-to-Stokes formulas are written under the
                # assumption that the “current” sheet of the Riemann surface of
                # log(s1+z) is the one containing s1·[1,+∞). In other words, the
                # incoming path should be equivalent to a path arriving “just
                # behind” s1 seen from s0 and from the right. This is the case
                # when it arrives from below the branch cut, or horizontally
                # from the right; otherwise, we can reduce to this case by
                # inserting a local monodromy matrix.
                side = s0.cmp_imag(s1)
                if side > 0 or side == 0 and s0.cmp_real(s1) < 0:
                    # XXX potential redundant computation, see _combine_edges
                    branch_fix = formal_monodromy(bdop, Point(s1, bdop), IC)
                else:
                    branch_fix = identity_matrix(IC, bdop.order())
                # Compute the block of the Stokes matrix corresponding to the
                # exponential parts associated to s0 and s1
                stokes_block[s0,s1] = (c2s_mat[s1] * branch_fix * tmat[s0,s1] *
                                       borel_mat[s0])
                logger.debug("%s -> %s, block=\n%s", s0, s1, stokes_block)
        stokes = block_matrix([[stokes_block[s0, s1] for s0 in sing]
                               for s1 in sing],
                              subdivide=True)
        stokes += 1
        yield dir, stokes


def stokes_dict(dop, eps=1e-16):
    r"""
    Stokes matrices of ``dop`` at the origin, as a dictionary.

    INPUT:

    - ``dop`` - differential operator
    - ``eps`` - tolerance parameter

    OUTPUT:

    A ``KeyConvertingDict`` mapping `e^{iω}` (viewed as an element of ``QQbar``)
    to the Stokes matrix in the direction `ω` for each singular direction `ω`.

    The Stokes matrices are expressed relative to a basis of solutions of
    ``dop`` obtained as follows:
    - For each exponential part `e^{α/x}`, consider the equation `L·z(x) = 0`
      obtained from ``dop·y(x) = 0`` by the change of dependent variable
      `y(x) = e^{α/x} z(x)`. The method
      :meth:`ore_algebra.differential_operator_1_1.DifferentialOperator.local_basis_expansions`
      can be used to compute a specific basis of the solutions of `L` free from
      exponentials. Multiply each basis element by `e^{α/x}` to obtain a
      solution of ``dop``.
    - Sort the exponential parts `e^{α/x}`
      * firstly by decreasing real part of `α`,
      * then by absolute value of the imaginary part,
      * then by decreasing imaginary part.
      Concatenate the partial bases from the previous step in this order.

    In particular, in the absence of oscillatory factors, the basis elements are
    strictly ordered by decreasing asymptotic dominance as `x → 0` with `x > 0`.

    EXAMPLES::

        sage: from ore_algebra import OreAlgebra
        sage: from ore_algebra.analytic.stokes import stokes_dict

        sage: Pol.<x> = QQ[]
        sage: Dop.<Dx> = OreAlgebra(Pol, 'Dx')

    Consider the Euler equation::

        sage: dop = x^3*Dx^2 + x*(x+1)*Dx - 1

    The potential Stokes direction are 0 and π::

        sage: stokes = stokes_dict(dop)
        sage: stokes.keys()
        dict_keys([1, -1])

    The Stokes matrix in the direction π is given by::

        sage: stokes[-1]
        [ 1.000000000000... [+/- ...] + [6.2831853071795...]*I]
        [                 0                  1.000000000000...]

    However, it turns out that there is no Stokes phenomenon in the
    direction 0::

        sage: stokes[1]
        [1.000000000000...                 0]
        [                0 1.000000000000...]

    (Note that compared to the numerical example given by Fauvet, Richard-Jung,
    and Thomann (2009, §3.3, (1)), our basis of solutions is in the reverse
    order, so that the Stokes matrices are transposed.)

    An example with three Stokes values on the real line::

        sage: dop = 2*(x^2*Dx)^3 + (x - 5)*(x^2*Dx)^2 + (2*x + 2)*(x^2*Dx) - 2*x
        sage: dop.generalized_series_solutions()
        [exp(-1/2*x^(-1))*x^(-1/2)*(1 - 2/3*x - 1/3*x^2 - 4/9*x^3 - 25/27*x^4 + O(x^5)),
         exp(-2*x^(-1))*x^(-1)*(1 + x + O(x^5)),
         x*(1 + 4*x + 45/2*x^2 + 333/2*x^3 + 3087/2*x^4 + O(x^5))]
        sage: stokes = stokes_dict(dop, RBF(1e-15))
        sage: stokes[1]
        [                  1.000000000000...                                   0                  0]
        [[+/- ...] + [-4.4562280437884...]*I                   1.000000000000...                  0]
        [ [4.8367983046245...] + [+/- ...]*I  [+/- ...] + [2.1708037636748...]*I  1.000000000000...]

    We can compute the Stokes constants to high precision::

        sage: stokes = stokes_dict(dop, RBF(1e-1000))
        sage: stokes[1][2,0]
        [4.8367983046...69279128366... +/- ...e-1000] + [+/- ...]*I

    Only singular points of single level 1 are currently supported::

        sage: stokes_dict(x^3*Dx - 1)
        Traceback (most recent call last):
        ...
        NotImplementedError: levels [2] ≠ 0, 1 are not supported

    See the documentation of the :mod:`ore_algebra.analytic.stokes` module for
    further examples.

    TESTS::

        sage: stokes_dict(Dop.one())
        {}
        sage: stokes_dict(Dx)
        {}

        sage: Pol1.<t> = QQ[]; Dop1.<Dt> = OreAlgebra(Pol1)
        sage: stokes_dict(t^3*Dt^2 + t*(t+1)*Dt - 1)[-1][0,1]
        [+/- ...] + [6.28318530717958...]*I

        sage: Pol1.<w> = Pol[]; Dop1.<Dw> = OreAlgebra(Pol1)
        sage: stokes_dict(w*Dw-1)
        Traceback (most recent call last):
        ...
        ValueError: unsupported base ring Univariate Polynomial Ring in x over Rational Field
    """
    return KeyConvertingDict(QQbar, stokes_matrices(dop, eps))


def _matrix_accuracy(mat):
    return min(c.accuracy() for c in mat.list())
