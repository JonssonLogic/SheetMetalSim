*KEYWORD
*TITLE
IMPLICIT_SPRINGBACK
$
*INCLUDE
$                                                                       FILENAME
deformed.k
$
$
$ -------------------------------------------------------------------------------
$
*CONTROL_TERMINATION
$   ENDTIM    ENDCYC     DTMIN    ENDENG    ENDMAS     NOSOL
      0.50         0        0.        0.        0.         0
*CONTROL_IMPLICIT_DYNAMICS
$    IMASS     GAMMA      BETA    TDYBIR    TDYDTH    TDYBUR     IRATE
         1       0.6      0.38        0.    1.E+28    1.E+28         1  
*CONTROL_IMPLICIT_GENERAL
$   IMFLAG       DT0    IMFORM      NSBS       IGS     CNSTN      FORM    ZERO_V
         1     0.001         2         1         2         0         0         0
*CONTROL_IMPLICIT_SOLUTION
$   NSOLVR    ILIMIT    MAXREF     DCTOL     ECTOL     RCTOL     LSTOL    ABSTOL
        12        15        20     0.001      0.01    1.E+10       0.9   1.0E-20
$    DNORM    DIVERG     ISTIF   NLPRINT    NLNORM   D3ITCTL     CPCHK
         1         1         1         2         4         1         0
$   ARCCTL    ARCDIR    ARCLEN    ARCMTH    ARCDMP    ARCPSI    ARCALF    ARCTIM
         0                   0         1         2        0.        0.        0.
$    LSMTD     LSDIR      IRAD      SRAD      AWGT      SRED
         4         2        0.        0.        0.        0.
*CONTROL_IMPLICIT_AUTO
$    IAUTO    ITEOPT    ITEWIN     DTMIN     DTMAX     DTEXP     KFAIL    KCYCLE
         1        50        15        0.    -20001        0.
*DEFINE_CURVE
$     LCID      SIDR       SFA       SFO      OFFA      OFFO    DATTYP
     20001         0        1.        1.        0.        0.         0
$                 A1                  O1
               0.000                0.02
             100.000                0.02
*CONTROL_ACCURACY
$      OSU       INN    PIDOSU      IACC
         1         4                   1
*CONTROL_CONTACT
$   SLSFAC    RWPNAL    ISLCHK    SHLTHK    PENOPT    THKCHG     ORIEN    ENMASS
        .1                   0         2         0         0         0         0
$   USRSTR    USRFRC     NSBCS    INTERM     XPENE     SSTHK      ECDT   TIEDPRJ
         0         0                   0        0.         1         0         0
$    SFRIC     DFRIC       EDC       VFC        TH     TH_SF    PEN_SF     PTSCL
        0.        0.        0.        0.        0.        0.        0.        0.
$   IGNORE    FRCENG   SKIPRWG    OUTSEG   SPOTSTP   SPOTDEL   SPOTHIN
        -2         0         0         0         0         0
$     ISYM    NSEROD    RWGAPS    RWGDTH     RWKSF      ICOV    SWRADF    ITHOFF
         0         0         0        0.        0.         0        0.         0
$   SHLEDG    PSTIFF    ITHCNT    TDCNOF     FTALL              SHLTRW
         1         0         0         0         0
*CONTROL_RIGID
$      LMF      JNTF    ORTHMD     PARTM    SPARSE    METALF    PLOTEL     RBSMS
         1         0         0         0         0         0         0         0
$   NORBIC   GJADSTF   GJADVSC   TJADSTF   TJADVSC
         0         0         0         0         0 
*CONTROL_ENERGY
$     HGEN      RWEN    SLNTEN     RYLEN
         2         2         2         2
*CONTROL_HOURGLASS
$      IHQ        QH
         6       0.1
*CONTROL_OUTPUT
$    NPOPT    NEECHO    NREFUP    IACCOP     OPIFS    IPNINT    IKEDIT    IFLUSH
         0         0         0         0        0.         0         0         0
$    IPRTF    IERODE   TET10S8    MSGMAX    IPCURV      GMDT   IP1DBLT      EOCS
         0         0         1         0         0        0.         0         0
$    TOLEV    NEWLEG    FRFREQ     MINFO    SOLSIG    MSGFLG    CDETOL       
         0         0         0         1         0         0      10.0
*CONTROL_SHELL
$   WRPANG     ESORT     IRNXX    ISTUPD    THEORY       BWC     MITER      PROJ
       20.         1        -1         1         0         0         0         0
$  ROTASCL    INTGRD    LAMSHT    CSTYP6    THSHEL
        1.         0         0         1         0
$   PSTUPD   SIDT4TU     CNTCO    ITSFLG    IRQUAD    W-MODE   STRETCH
         0         0         0         0         0               
$   NFAIL1    NFAIL4   PSNFAIL    KEEPCS     DELFR   DRCPSID    DRCPRM   INTPERR
                             0         0         0         0        0.
*CONTROL_SOLID
$    ESORT    FMATRX   NIPTETS    SWLOCL    PSFAIL   T10JTOL      ICOH    TET13K
         1         0         4         1         0        0.         0         0
$ ------------------------------------------------------------------------------
$ ----------------------------------  SHEETMETAL  ------------------------------
$ ------------------------------------------------------------------------------
*INTERFACE_SPRINGBACK_LSDYNA
$     PSID      NSHV     FTYPE               FTNSR    NTHHSV     RFLAG   INTSTRN
         1                   0                   0                   0         1
$ ------------------------------------------------------------------------------
$ --------------------------------- DATABASE CARDS -----------------------------
$ ------------------------------------------------------------------------------
*DATABASE_FORMAT
$    IFORM   IBINARY
         0
*DEFINE_CURVE
$     LCID      SIDR       SFA       SFO      OFFA      OFFO    DATTYP
   1000000         0        1.        1.        0.        0.         0
$                 A1                  O1
               0.000               1.E-3
             100.000               1.E-3
*DATABASE_BNDOUT
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_DEFORC
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_ELOUT
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_GLSTAT
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_JNTFORC
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_MATSUM
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_NODOUT
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_RBDOUT
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_RCFORC
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_SPCFORC
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_RWFORC
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_SECFORC
$       DT    BINARY      LCUR     IOOPT   OPTION1   OPTION2   OPTION3   OPTION4
         0         3   1000000
*DATABASE_BINARY_D3THDT
$  DT/CYCL   LCDT/NR      BEAM     NPLTC    PSETID
         0   1000000
*DEFINE_CURVE
$     LCID      SIDR       SFA       SFO      OFFA      OFFO    DATTYP
   1000001         0        1.        1.        0.        0.         0
$                 A1                  O1
               0.000               1.E-2
             100.000               1.E-2
*DATABASE_BINARY_D3PLOT
$  DT/CYCL   LCDT/NR      BEAM     NPLTC    PSETID
         0   1000001
$    IOOPT      RATE    CUTOFF    WINDOW      TYPE      PSET  
         1
*DATABASE_EXTENT_BINARY
$    NEIPH     NEIPS    MAXINT    STRFLG    SIGFLG    EPSFLG    RLTFLG    ENGFLG
        50        50         5         1         1         1         1         1
$   CMPFLG    IEVERP    BEAMIP     DCOMP      SHGE     STSSZ    N3THDT   IALEMAT
         0         0         4         1         1         1         2         1
$  NINTSLD   PKP_SEN      SCLP     HYDRO     MSSCL     THERM    INTOUT    NODOUT
         0         0        1.         0         0         0
$       DT    RESPLT     NEIPB
         0         1         0
*END