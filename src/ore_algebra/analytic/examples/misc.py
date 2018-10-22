r"""
Miscellaneous examples

An example kindly provided by Christoph Koutschan::

    sage: from ore_algebra.analytic.examples.misc import koutschan1
    sage: koutschan1.dop.numerical_solution(koutschan1.ini, [0, 84])
    [0.011501537469552017...]

One by Bruno Salvy, where we follow a branch of the solutions of an algebraic
equation::

    sage: from ore_algebra.analytic.examples.misc import salvy1_pol, salvy1_dop
    sage: Pols.<z> = QQ[]
    sage: a = AA.polynomial_root(54*z**3+324*z**2-4265*z+432, RIF(0.1, 0.11))
    sage: roots = salvy1_pol(z=a).univariate_polynomial().roots(QQbar)
    sage: val = salvy1_dop.numerical_solution([0, 0, 0, 0, 0, 1/2], [0, a]) # long time (8.8 s)
    sage: CBF100 = ComplexBallField(100)
    sage: [r for (r, _) in roots if CBF100(r) in val]                       # long time
    [0.0108963334211605...]

An example provided by Steve Melczer which used to trigger an issue with the
numerical analytic continuation code::

    sage: from ore_algebra.analytic.examples.misc import melczer1
    sage: rts = melczer1.leading_coefficient().roots(QQbar, multiplicities=False)
    sage: melczer1.numerical_transition_matrix([0, rts[1]])[0, 0]
    [4.64191240683...] + [-0.01596122801...]*I
    sage: melczer1.local_basis_expansions(rts[1])
    [1 + (1269/32*a+3105/28)*(z + 0.086...? + 0.069...*I)^4 + ...,
     sqrt(z + 0.086...? + 0.069...*I) + (365/96*a+13/3)*(z + 0.086...? + 0.069...*I)^(3/2) - ...,
     ...]
"""
import collections

from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from ore_algebra import DifferentialOperators

IVP = collections.namedtuple("IVP", ["dop", "ini"])

DiffOps_a, a, Da = DifferentialOperators(QQ, 'a')
koutschan1 = IVP(
    dop = (1315013644371957611900*a**2+263002728874391522380*a+13150136443719576119)*Da**3
        + (2630027288743915223800*a**2+16306169190212274387560*a+1604316646133788286518)*Da**2
        + (1315013644371957611900*a**2-39881765316802329075320*a+35449082663034775873349)*Da
        + (-278967152068515080896550+6575068221859788059500*a),
    ini = [ QQ(5494216492395559)/3051757812500000000000000000000,
            QQ(6932746783438351)/610351562500000000000000000000,
            1/QQ(2) * QQ(1142339612827789)/19073486328125000000000000000 ]
)

y, z = PolynomialRing(QQ, ['y', 'z']).gens()
salvy1_pol = (16*y**6*z**2 + 8*y**5*z**3 + y**4*z**4 + 128*y**5*z**2 + 48*y**4*z**3 +
        4*y**3*z**4 + 32*y**5* z + 372*y**4*z**2 + 107*y**3*z**3 + 6*y**2*z**4 +
        88*y**4*z + 498*y**3*z**2 + 113*y**2*z**3 + 4*y*z**4 + 16*y**4 + 43*y**3*z +
        311*y**2*z**2 + 57*y*z**3 + z**4 + 24*y**3 - 43*y**2*z + 72*y*z **2 + 11*z**3 +
        12*y**2 - 30*y*z - z**2 + 2*y)
DiffOps_z, z, Dz = DifferentialOperators(QQ, 'z')
salvy1_dop = ((71820*z**41 + 22638420*z**40 + 706611850*z**39 - 27125189942*z**38 -
        1014313164418*z**37 - 2987285491626*z**36 + 143256146804484*z**35 +
        595033302717820*z**34 - 8471861990006953*z**33 + 22350994766224977*z**32 +
        199821041784996648*z**31 - 11402401137364528368*z**30 -
        20097653091034863945*z**29 + 779360354402528630973*z**28 -
        176989790944223286690*z**27 - 21147240812021497949406*z**26 +
        142998531993721111599972*z**25 + 80316114769669665621696*z**24 -
        5307473733185494433298552*z**23 + 7203584446884104208728712*z**22 +
        35801597981121411452825952*z**21 + 3263398824907862040304272*z**20 -
        36655644766584223667752320*z**19 - 150953800574563497880271616*z**18 +
        119544860701204579715524608*z**17 + 71974080926245507955960832*z**16 +
        25422428208418632702600192*z**15
        - 97009343834279788623234048*z**14 + 30442156869153615816081408*z**13
        - 4512522437805042635751424*z**12 + 661786684296532253081600*z**11 -
        82017873705407751913472*z**10 + 4174868398581661827072*z**9 -
        3478618055343341568*z**8 - 1261658236927344640*z**7 -
        44373111021240320*z**6 + 3246995275776000*z**5)*Dz**6
    + (1508220*z**40 + 491150520*z**39 + 14150735900*z**38 - 696715582428*z**37
        - 22217607684928*z**36 - 11824861415940*z**35 + 3377569342519110*z**34 +
        6363032094643108*z**33 - 175716240466949786*z**32 +
        855613611427762866*z**31 - 4551321215387777004*z**30 -
        265500396363760299360*z**29 + 186683361500557485642*z**28 +
        16074356319671937220698*z**27 + 1234135482266536513710*z**26 -
        387762937754593628456160*z**25 + 759404763793204572495792*z**24 +
        2261325034838887233477504*z**23 - 41274301561246646794131000*z**22 +
        75859287634577872636047648*z**21 + 345933336032358635561167920*z**20
        - 75770662035007030703670816*z**19 - 548127759327893237397045888*z**18 -
        1984770925517181472514114304*z**17 + 2091936018809166141930723840*z**16 +
        1192632549738707598170489856*z**15 + 267266923340533902381029376*z**14 -
        1868900638964812073735000064*z**13 + 613553965698628256330317824*z**12 -
        77607719946919803394113536*z**11 + 7371455721053484707217408*z**10 -
        791442539759097593987072*z**9 + 39762980090782414798848*z**8 -
        28949523235501768704*z**7 - 13194933109050572800*z**6 -
        635602009587712000*z**5 + 43834436222976000*z**4)*Dz**5
    + (9759540*z**39 + 3300863160*z**38 + 87137559810*z**37 - 5407470459530*z**36 -
        148017196969880*z**35 + 327169577099540*z**34 + 23855226876775400*z**33 -
        15119864088662770*z**32 - 1068958213416098195*z**31 +
        10070733194952785265*z**30 - 94203687357400320315*z**29 -
        2119128812313514338075*z**28 + 6015947971641580585500*z**27 +
        118902572901421890849600*z**26 - 66475503708341321459130*z**25 -
        2664998571913084998527400*z**24 - 1442947621702924546389360*z**23 +
        21374730535662210377732400*z**22 - 5972229387165285508315080*z**21 +
        125324729687473129775650560*z**20 + 536692069128654755907333840*z**19 -
        674002019392465324114334880*z**18
        - 1471372065391435603680706560*z**17 - 5677072446499749526066892160*z**16
        + 9542146757872199793164052480*z**15 + 5120843179458923410892014080*z**14
        - 122923795202985634324869120*z**13 - 10745729910232387237212733440*z**12
        + 3764895058887333176234557440*z**11 - 429936803911646516743127040*z**10
        + 21020383360468725284864000*z**9 - 1290297906707895746560000*z**8 +
        54129401362049463746560*z**7 + 268284667125091532800*z**6 -
        28728185968268410880*z**5 - 2622325933641564160*z**4 +
        156577327742976000*z**3)*Dz**4
    + (22056720*z**38 + 7800834720*z**37 + 187099626630*z**36 -
            14489632628200*z**35 - 340288650977140*z**34 + 1821599039970040*z**33
            + 56668655708213950*z**32 - 193347619586203760*z**31 -
            1779712936449988285*z**30 + 34782281241372628470*z**29 -
            457152676877903439975*z**28 - 5949470068797299899140*z**27 +
            32822481515490323168580*z**26 + 323679970477791577786560*z**25 -
            753142149501904588308120*z**24 - 6944123449957281404877120*z**23 +
            1249683063497933229678000*z**22 + 64983819922455028829947680*z**21 +
            152023062017110121268050880*z**20 - 162585001615506352297680000*z**19
            - 658948691616877006273697280*z**18 -
            904838325157075863153976320*z**17 +
            1665021268927495995942858240*z**16 - 81968505388096146560432640*z**15
            + 8375791947054942984297768960*z**14 +
            3676564359591337510548602880*z**13 -
            5230040870261114310516203520*z**12 -
            20479559361125449192901713920*z**11 +
            7895429046279773990603980800*z**10 - 870059015693328423026688000*z**9
            + 18132153175565342597447680*z**8 + 948962653419194086850560*z**7 -
            88684921159591080755200*z**6 + 1632614837720459509760*z**5 -
            4520478397872209920*z**4 - 3596953162423992320*z**3 +
            140342351364096000*z**2)*Dz**3
    + (13693680*z**37 + 5111346240*z**36 + 110337277050*z**35 -
            10616572896900*z**34 - 212616907355220*z**33 + 1907197694065680*z**32
            + 35086470242555490*z**31 - 230830962691484460*z**30 -
            119801336414582715*z**29 + 26838037841767027380*z**28 -
            560160775489343242545*z**27 - 4198797970570866711510*z**26 +
            42743928885060777438960*z**25 + 224466018637260564654120*z**24 -
            1268908050017507124479400*z**23
            - 4379979463524457535039760*z**22 + 15155482733928330881828400*z**21
            + 40794045636529987278102720*z**20 - 37644049223426983435911360*z**19
            - 58823741580795635845155840*z**18 -
            448474984893359633937991680*z**17 + 41591801685730020441454080*z**16
            + 3162304645220555725940812800*z**15 +
            2319883018843619208638315520*z**14 -
            8393145340874982467702722560*z**13 -
            6681520568322378041767096320*z**12 -
            8252703629920220034552053760*z**11 -
            9629037566950972555498291200*z**10 +
            4387995986890067861013135360*z**9 - 461514254064285343458263040*z**8
            + 522858309517567202426880*z**7 + 634546595151770875330560*z**6 -
            28049016515447614341120*z**5 + 777846307956562329600*z**4 -
            7008788477714104320*z**3 - 1553682343196098560*z**2 +
            2164663517184000*z)*Dz**2
    + (- 41879040*z**33 - 1416307200*z**32 + 148941814560*z**31 +
            3270298516800*z**30 - 11477419141440*z**29 - 2594539713258240*z**28 -
            51745363970093280*z**27 + 745698123298307520*z**26 +
            22802877042886843920*z**25 + 14050350666949553280*z**24 -
            2048447965484252604240*z**23 - 2228764713877225222560*z**22 +
            89453205322869720983040*z**21 - 46789880409365742501120*z**20 -
            2123767277799444443439360*z**19 + 724858375756050858078720*z**18 +
            6269080959998916108537600*z**17 + 88970832949842762649989120*z**16 +
            134828145628568403921400320*z**15 - 526784933100386618307394560*z**14
            - 2464815884998450540389719040*z**13 -
            3504246799326542509131878400*z**12 -
            3785383718150451876235284480*z**11 -
            1818465489663730171421736960*z**10 + 155064625280607257421742080*z**9
            + 47441424650557360135864320*z**8 + 43137927034599581118627840*z**7
            - 11239734089998880546488320*z**6 + 504783801825732109271040*z**5 +
            10521549814703849472000*z**4 - 811692880841649684480*z**3 -
            1636617689235456000*z**2 - 141564870855229440*z -
            2164663517184000)*Dz
    + (- 3697966841856000 + 41879040*z**32 + 544427520*z**31 - 162356006400*z**30
            - 251676096000*z**29 - 3285830607360*z**28 + 570977399938560*z**27 +
            40948236792921600*z**26 - 493076168891343360*z**25 -
            15680703841739688960*z**24 + 34853169398214896640*z**23 +
            1282924695185330964480*z**22 - 2634867247875329986560*z**21 -
            31543463403883538657280*z**20 + 112726502509909108838400*z**19 -
            197290858158049402183680*z**18 + 1743747637921540472586240*z**17 -
            6464161036183311324610560*z**16 + 7279692122187953521459200*z**15 +
            3140449849104166786498560*z**14 - 6705947281208374709452800*z**13
            - 14304923501365693808640000*z**12 + 33533652518766896672931840*z**11
            - 23650577729697452583813120*z**10 + 3923835475521556599275520*z**9 +
            2256201135091492721786880*z**8 - 235487576779477147975680*z**7
            - 585638701894459069562880*z**6 - 27312208046701695467520*z**4 +
            972607606705430200320*z**3 - 248157347732520960*z +
            212916818855030905896960*z**5 + 21162675253133967360*z**2))


DiffOps_z, z, Dz = DifferentialOperators(QQ, 'z')
melczer1 = ((81*z**5 + 14*z**4 + z**3)*Dz**5 + (1296*z**4 + 175*z**3 + 9*z**2)*Dz**4
        + (6075*z**3 + 594*z**2 + 19*z)*Dz**3 + (9315*z**2 + 573*z + 8)*Dz**2
        + (3726*z + 102)*Dz + 162)
