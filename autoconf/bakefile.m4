dnl ---------------------------------------------------------------------------
dnl Support macros for makefiles generated by BAKEFILE.
dnl ---------------------------------------------------------------------------

dnl Lots of compiler & linker detection code contained here was taken from
dnl wxWindows configure.in script (see http://www.wxwindows.org)



dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_GNUMAKE
dnl
dnl Detects GNU make
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_GNUMAKE,
[
    dnl does make support "-include" (only GNU make does AFAIK)?
    AC_CACHE_CHECK([if make is GNU make], bakefile_cv_prog_makeisgnu,
    [
        if ( ${SHELL-sh} -c "${MAKE-make} --version" 2> /dev/null |
                egrep -s GNU > /dev/null); then
            bakefile_cv_prog_makeisgnu="yes"
        else
            bakefile_cv_prog_makeisgnu="no"
        fi
    ])

    if test "x$bakefile_cv_prog_makeisgnu" = "xyes"; then
        IF_GNU_MAKE=""
    else
        IF_GNU_MAKE="#"
    fi
    AC_SUBST(IF_GNU_MAKE)
])

dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_PLATFORM
dnl
dnl Detects platform and sets PLATFORM_XXX variables accordingly
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_PLATFORM,
[
    PLATFORM_UNIX=0
    PLATFORM_WIN32=0
    PLATFORM_MSDOS=0
    PLATFORM_MAC=0
    PLATFORM_MACOSX=0
    PLATFORM_OS2=0

    if test "x$BAKEFILE_FORCE_PLATFORM" = "x"; then 
        case "${BAKEFILE_HOST}" in
            *-*-cygwin* | *-*-mingw32* )
                PLATFORM_WIN32=1
            ;;
            *-pc-msdosdjgpp )
                PLATFORM_MSDOS=1
            ;;
            *-pc-os2_emx | *-pc-os2-emx )
                PLATFORM_OS2=1
            ;;
            powerpc-*-darwin* )
                PLATFORM_MAC=1
                PLATFORM_MACOSX=1
            ;;
            * )
                PLATFORM_UNIX=1
            ;;
        esac
    else
        case "$BAKEFILE_FORCE_PLATFORM" in
            win32 )
                PLATFORM_WIN32=1
            ;;
            msdos )
                PLATFORM_MSDOS=1
            ;;
            os2 )
                PLATFORM_OS2=1
            ;;
            darwin )
                PLATFORM_MAC=1
                PLATFORM_MACOSX=1
            ;;
            unix )
                PLATFORM_UNIX=1
            ;;
            * )
                AC_MSG_ERROR([Unknown platform: $BAKEFILE_FORCE_PLATFORM])
            ;;
        esac
    fi

    AC_SUBST(PLATFORM_UNIX)
    AC_SUBST(PLATFORM_WIN32)
    AC_SUBST(PLATFORM_MSDOS)
    AC_SUBST(PLATFORM_MAC)
    AC_SUBST(PLATFORM_MACOSX)
    AC_SUBST(PLATFORM_OS2)
])


dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_PLATFORM_SPECIFICS
dnl
dnl Sets misc platform-specific settings
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_PLATFORM_SPECIFICS,
[
    AC_ARG_ENABLE([omf], [  --enable-omf            use OMF object format (OS/2)],
                  [bk_os2_use_omf="$enableval"])
    
    case "${BAKEFILE_HOST}" in
      *-*-darwin* )
        dnl For Unix to MacOS X porting instructions, see:
        dnl http://fink.sourceforge.net/doc/porting/porting.html
        CFLAGS="$CFLAGS -fno-common"
        CXXFLAGS="$CXXFLAGS -fno-common"
        ;;

      *-pc-os2_emx | *-pc-os2-emx )
        if test "x$bk_os2_use_omf" = "xyes" ; then
            AR=emxomfar
            RANLIB=:
            LDFLAGS="-Zomf $LDFLAGS"
            CFLAGS="-Zomf $CFLAGS"
            CXXFLAGS="-Zomf $CXXFLAGS"
            OS2_LIBEXT=".lib"
        else
            OS2_LIBEXT=".a"
        fi
        ;;
    esac
])

dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_SUFFIXES
dnl
dnl Detects shared various suffixes for shared libraries, libraries, programs,
dnl plugins etc.
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_SUFFIXES,
[
    SO_SUFFIX="so"
    SO_SUFFIX_MODULE="so"
    EXEEXT=""
    LIBPREFIX="lib"
    LIBEXT=".a"
    DLLPREFIX="lib"
    DLLPREFIX_MODULE=""
    DLLIMP_SUFFIX=""
    
    case "${BAKEFILE_HOST}" in
        *-hp-hpux* )
            SO_SUFFIX="sl"
            SO_SUFFIX_MODULE="sl"
        ;;
        *-*-aix* )
            dnl quoting from
            dnl http://www-1.ibm.com/servers/esdd/articles/gnu.html:
            dnl     Both archive libraries and shared libraries on AIX have an
            dnl     .a extension. This will explain why you can't link with an
            dnl     .so and why it works with the name changed to .a.
            SO_SUFFIX="a"
            SO_SUFFIX_MODULE="a"
        ;;
        *-*-cygwin* | *-*-mingw32* )
            SO_SUFFIX="dll"
            SO_SUFFIX_MODULE="dll"
            DLLIMP_SUFFIX="dll.a"
            EXEEXT=".exe"
            DLLPREFIX=""
        ;;
        *-pc-msdosdjgpp )
            EXEEXT=".exe"
            DLLPREFIX=""
        ;;
        *-pc-os2_emx | *-pc-os2-emx )
            SO_SUFFIX="dll"
            SO_SUFFIX_MODULE="dll"
            DLLIMP_SUFFIX=$OS2_LIBEXT
            EXEEXT=".exe"
            DLLPREFIX=""
            LIBPREFIX=""
            LIBEXT=$OS2_LIBEXT
        ;;
        powerpc-*-darwin* )
            SO_SUFFIX="dylib"
            SO_SUFFIX_MODULE="bundle"
        ;;
    esac

    if test "x$DLLIMP_SUFFIX" = "x" ; then
        DLLIMP_SUFFIX="$SO_SUFFIX"
    fi

    AC_SUBST(SO_SUFFIX)
    AC_SUBST(SO_SUFFIX_MODULE)
    AC_SUBST(DLLIMP_SUFFIX)
    AC_SUBST(EXEEXT)
    AC_SUBST(LIBPREFIX)
    AC_SUBST(LIBEXT)
    AC_SUBST(DLLPREFIX)
    AC_SUBST(DLLPREFIX_MODULE)
])


dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_SHARED_LD
dnl
dnl Detects command for making shared libraries, substitutes SHARED_LD_CC
dnl and SHARED_LD_CXX.
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_SHARED_LD,
[
    dnl Defaults for GCC and ELF .so shared libs:
    SHARED_LD_CC="\$(CC) -shared -o"
    SHARED_LD_CXX="\$(CXX) -shared -o"

    dnl the extra compiler flags needed for compilation of shared library
    if test "x$GCC" = "xyes"; then
        dnl the switch for gcc is the same under all platforms
        PIC_FLAG="-fPIC"
    fi

    case "${BAKEFILE_HOST}" in
      *-hp-hpux* )
        dnl default settings are good for gcc but not for the native HP-UX
        if test "x$GCC" = "xyes"; then
            dnl -o flag must be after PIC flag
            SHARED_LD_CC="${CC} -shared ${PIC_FLAG} -o"
            SHARED_LD_CXX="${CXX} -shared ${PIC_FLAG} -o"
        else
            dnl no idea why it wants it, but it does
            LDFLAGS="$LDFLAGS -L/usr/lib"

            SHARED_LD_CC="${CC} -b -o"
            SHARED_LD_CXX="${CXX} -b -o"
            PIC_FLAG="+Z"
        fi
      ;;

      *-*-linux* )
        if test "x$GCC" != "xyes"; then
            AC_CACHE_CHECK([for Intel compiler], bakefile_cv_prog_icc,
            [
                AC_TRY_COMPILE([],
                    [
                        #ifndef __INTEL_COMPILER
                        #error Not icc
                        #endif
                    ],
                    bakefile_cv_prog_icc=yes,
                    bakefile_cv_prog_icc=no
                )
            ])
            if test "$bakefile_cv_prog_icc" = "yes"; then
                PIC_FLAG="-KPIC"
            fi
        fi
      ;;

      *-*-solaris2* )
        if test "x$GCC" != xyes ; then
            SHARED_LD_CC="${CC} -G -o"
            SHARED_LD_CXX="${CXX} -G -o"
            PIC_FLAG="-KPIC"
        fi
      ;;

      *-*-darwin* )
        dnl Most apps benefit from being fully binded (its faster and static
        dnl variables initialized at startup work).
        dnl This can be done either with the exe linker flag -Wl,-bind_at_load
        dnl or with a double stage link in order to create a single module
        dnl "-init _wxWindowsDylibInit" not useful with lazy linking solved

        dnl If using newer dev tools then there is a -single_module flag that
        dnl we can use to do this, otherwise we'll need to use a helper
        dnl script.  Check the version of gcc to see which way we can go:
        AC_CACHE_CHECK([for gcc 3.1 or later], wx_cv_gcc31, [
           AC_TRY_COMPILE([],
               [
                   #if (__GNUC__ < 3) || \
                       ((__GNUC__ == 3) && (__GNUC_MINOR__ < 1))
                       #error old gcc
                   #endif
               ],
               [
                   wx_cv_gcc31=yes
               ],
               [
                   wx_cv_gcc31=no
               ]
           )
        ])
        if test "$wx_cv_gcc31" = "no"; then
            cat <<EOF >shared-ld-sh
#!/bin/sh
#-----------------------------------------------------------------------------
#-- Name:        distrib/mac/shared-ld-sh
#-- Purpose:     Link a mach-o dynamic shared library for Darwin / Mac OS X
#-- Author:      Gilles Depeyrot
#-- Copyright:   (c) 2002 Gilles Depeyrot
#-- Licence:     any use permitted
#-----------------------------------------------------------------------------

verbose=0
args=""
objects=""
linking_flag="-dynamiclib"

while test \${#} -gt 0; do
    case \${1} in

       -v)
        verbose=1
        ;;

       -o|-compatibility_version|-current_version|-framework|-undefined|-install_name)
        # collect these options and values
        args="\${args} \${1} \${2}"
        shift
        ;;

       -l*|-L*|-flat_namespace|-headerpad_max_install_names)
        # collect these options
        args="\${args} \${1}"
        ;;

       -dynamiclib|-bundle)
        linking_flag="\${1}"
        ;;

       -*)
        echo "shared-ld: unhandled option '\${1}'"
        exit 1
        ;;

        *.o | *.a | *.dylib)
        # collect object files
        objects="\${objects} \${1}"
        ;;

        *)
        echo "shared-ld: unhandled argument '\${1}'"
        exit 1
        ;;

    esac
    shift
done

#
# Link one module containing all the others
#
if test \${verbose} = 1; then
    echo "c++ -r -keep_private_externs -nostdlib \${objects} -o master.\$\$.o"
fi
c++ -r -keep_private_externs -nostdlib \${objects} -o master.\$\$.o
status=\$?
if test \${status} != 0; then
    exit \${status}
fi

#
# Link the shared library from the single module created
#
if test \${verbose} = 1; then
    echo "cc \${linking_flag} master.\$\$.o \${args}"
fi
c++ \${linking_flag} master.\$\$.o \${args}
status=\$?
if test \${status} != 0; then
    exit \${status}
fi

#
# Remove intermediate module
#
rm -f master.\$\$.o

exit 0
EOF
            chmod +x shared-ld-sh

            dnl Use the shared-ld-sh helper script
            SHARED_LD_CC="`pwd`/shared-ld-sh -dynamiclib -headerpad_max_install_names -o"
            SHARED_LD_MODULE_CC="`pwd`/shared-ld-sh -bundle -headerpad_max_install_names -o"
            SHARED_LD_CXX="$SHARED_LD_CC"
            SHARED_LD_MODULE_CXX="$SHARED_LD_MODULE_CC"
        else
            dnl Use the -single_module flag and let the linker do it for us
            SHARED_LD_CC="\${CC} -dynamiclib -single_module -headerpad_max_install_names -o"
            SHARED_LD_MODULE_CC="\${CC} -bundle -single_module -headerpad_max_install_names -o"
            SHARED_LD_CXX="\${CXX} -dynamiclib -single_module -headerpad_max_install_names -o"
            SHARED_LD_MODULE_CXX="\${CXX} -bundle -single_module -headerpad_max_install_names -o"
        fi

        PIC_FLAG="-dynamic -fPIC"
      ;;

      *-*-aix* )
        dnl default settings are ok for gcc
        if test "x$GCC" != "xyes"; then
            dnl the abs path below used to be hardcoded here so I guess it must
            dnl be some sort of standard location under AIX?
            AC_CHECK_PROG(AIX_CXX_LD, makeC++SharedLib,
                          makeC++SharedLib, /usr/lpp/xlC/bin/makeC++SharedLib)
            dnl FIXME - what about makeCSharedLib?            
            SHARED_LD_CC="$AIX_CC_LD -p 0 -o"
            SHARED_LD_CXX="$AIX_CXX_LD -p 0 -o"
        fi
      ;;

      *-*-beos* )
        dnl can't use gcc under BeOS for shared library creation because it
        dnl complains about missing 'main'
        SHARED_LD_CC="${LD} -shared -o"
        SHARED_LD_CXX="${LD} -shared -o"
      ;;

      *-*-irix* )
        dnl default settings are ok for gcc
        if test "x$GCC" != "xyes"; then
            PIC_FLAG="-KPIC"
        fi
      ;;
      
      *-*-cygwin* | *-*-mingw32* )
        PIC_FLAG=""
      ;;

      *-pc-os2_emx | *-pc-os2-emx )
        SHARED_LD_CC="dllar.sh -o"
        SHARED_LD_CXX="dllar.sh -o"
        PIC_FLAG=""
      ;;
      
      *-*-freebsd* | *-*-openbsd* | *-*-netbsd* | \
      *-*-sunos4* | \
      *-*-osf* | \
      *-*-dgux5* | \
      *-*-sysv5* )
        dnl defaults are ok
      ;;

      *)
        AC_MSG_ERROR(unknown system type $BAKEFILE_HOST.)
    esac

    if test "x$SHARED_LD_MODULE_CC" = "x" ; then
        SHARED_LD_MODULE_CC="$SHARED_LD_CC"
    fi
    if test "x$SHARED_LD_MODULE_CXX" = "x" ; then
        SHARED_LD_MODULE_CXX="$SHARED_LD_CXX"
    fi

    AC_SUBST(SHARED_LD_CC)
    AC_SUBST(SHARED_LD_CXX)
    AC_SUBST(SHARED_LD_MODULE_CC)
    AC_SUBST(SHARED_LD_MODULE_CXX)
    AC_SUBST(PIC_FLAG)
])


dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_SHARED_VERSIONS
dnl
dnl Detects linker options for attaching versions (sonames) to shared  libs.
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_SHARED_VERSIONS,
[
    USE_SOVERSION=0
    USE_SOVERLINUX=0
    USE_SOVERSOLARIS=0
    USE_SOSYMLINKS=0
    USE_MACVERSION=0
    SONAME_FLAG=

    case "${BAKEFILE_HOST}" in
      *-*-linux* )
        SONAME_FLAG="-Wl,-soname,"
        USE_SOVERSION=1
        USE_SOVERLINUX=1
        USE_SOSYMLINKS=1
      ;;

      *-*-solaris2* )
        SONAME_FLAG="-h "
        USE_SOVERSION=1
        USE_SOVERSOLARIS=1
        USE_SOSYMLINKS=1
      ;;

      *-*-darwin* )
        USE_MACVERSION=1
        USE_SOVERSION=1
        USE_SOSYMLINKS=1
      ;;      
    esac

    AC_SUBST(USE_SOVERSION)
    AC_SUBST(USE_SOVERLINUX)
    AC_SUBST(USE_SOVERSOLARIS)
    AC_SUBST(USE_MACVERSION)
    AC_SUBST(USE_SOSYMLINKS)
    AC_SUBST(SONAME_FLAG)
])


dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_DEPS
dnl
dnl Detects available C/C++ dependency tracking options
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_DEPS,
[
    AC_MSG_CHECKING([for dependency tracking method])
    DEPS_TRACKING=0

    if test "x$GCC" = "xyes"; then
        DEPSMODE=gcc
        DEPS_TRACKING=1
        case "${BAKEFILE_HOST}" in
            powerpc-*-darwin* )
                dnl -cpp-precomp (the default) conflicts with -MMD option
                dnl used by bk-deps (see also http://developer.apple.com/documentation/Darwin/Conceptual/PortingUnix/compiling/chapter_4_section_3.html)
                DEPSFLAG_GCC="-no-cpp-precomp -MMD"
            ;;
            * )
                DEPSFLAG_GCC="-MMD"
            ;;
        esac
        AC_MSG_RESULT([gcc])
    else
        AC_MSG_RESULT([none])
    fi

    if test $DEPS_TRACKING = 1 ; then
        cat <<EOF >bk-deps
#!/bin/sh

# This script is part of Bakefile (http://bakefile.sourceforge.net) autoconf
# script. It is used to track C/C++ files dependencies in portable way.
#
# Permission is given to use this file in any way.

DEPSMODE=$DEPSMODE
DEPSDIR=.deps
DEPSFLAG_GCC="$DEPSFLAG_GCC"

mkdir -p \$DEPSDIR

if test \$DEPSMODE = gcc ; then
    \${*} \${DEPSFLAG_GCC}
    status=\${?}
    if test \${status} != 0 ; then
        exit \${status}
    fi
    # move created file to the location we want it in:
    while test \${#} -gt 0; do
        case "\${1}" in
            -o )
                shift
                objfile=\${1}
            ;;
            -* )
            ;;
            * )
                srcfile=\${1}
            ;;
        esac
        shift
    done
    depfile=\`basename \$srcfile | sed -e 's/\..*$/.d/g'\`
    depobjname=\`echo \$depfile |sed -e 's/\.d/.o/g'\`
    if test -f \$depfile ; then
        sed -e "s,\$depobjname:,\$objfile:,g" \$depfile >\${DEPSDIR}/\${objfile}.d
        rm -f \$depfile
    else
        depfile=\`basename \$objfile | sed -e 's/\..*$/.d/g'\`
        if test -f \$depfile ; then
            sed -e "/^\$objfile/!s,\$depobjname:,\$objfile:,g" \$depfile >\${DEPSDIR}/\${objfile}.d
            rm -f \$depfile
        fi
    fi
    exit 0
else
    \${*}
    exit \${?}
fi
EOF
        chmod +x bk-deps
    fi
    
    AC_SUBST(DEPS_TRACKING)
])

dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_CHECK_BASIC_STUFF
dnl
dnl Checks for presence of basic programs, such as C and C++ compiler, "ranlib"
dnl or "install"
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_CHECK_BASIC_STUFF,
[
    AC_PROG_RANLIB
    AC_PROG_INSTALL
    AC_PROG_LN_S

    AC_PROG_MAKE_SET
    AC_SUBST(MAKE_SET)
    
    AC_CHECK_TOOL(AR, ar, ar)
    AC_CHECK_TOOL(STRIP, strip, :)
    AC_CHECK_TOOL(NM, nm, :)

    case ${BAKEFILE_HOST} in
        *-hp-hpux* )
            INSTALL_DIR="mkdir"
            ;;
        *)  INSTALL_DIR="$INSTALL -d"
            ;;
    esac
    AC_SUBST(INSTALL_DIR)

    LDFLAGS_GUI=
    case ${BAKEFILE_HOST} in
        *-*-cygwin* | *-*-mingw32* )
        LDFLAGS_GUI="-mwindows"
    esac
    AC_SUBST(LDFLAGS_GUI)
])


dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_RES_COMPILERS
dnl
dnl Checks for presence of resource compilers for win32 or mac
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_RES_COMPILERS,
[
    RESCOMP=
    SETFILE=

    case ${BAKEFILE_HOST} in 
        *-*-cygwin* | *-*-mingw32* )
            dnl Check for win32 resources compiler:
            if test "$build" != "$host" ; then
                RESCOMP=$host_alias-windres
            else
                AC_CHECK_PROG(RESCOMP, windres, windres, windres)
            fi
         ;;
 
      *-*-darwin* )
            AC_CHECK_PROG(RESCOMP, Rez, Rez, /Developer/Tools/Rez)
            AC_CHECK_PROG(SETFILE, SetFile, SetFile, /Developer/Tools/SetFile)
        ;;
    esac

    AC_SUBST(RESCOMP)
    AC_SUBST(SETFILE)
])

dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE_PRECOMP_HEADERS
dnl
dnl Check for precompiled headers support (GCC >= 3.4)
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE_PRECOMP_HEADERS,
[

    AC_ARG_ENABLE([precomp-headers],
                  [  --disable-precomp-headers  don't use precompiled headers even if compiler can],
                  [bk_use_pch="$enableval"])

    GCC_PCH=0

    if test "x$bk_use_pch" = "x" -o "x$bk_use_pch" = "xyes" ; then
        if test "x$GCC" = "xyes"; then
            dnl test if we have gcc-3.4:
            AC_MSG_CHECKING([if the compiler supports precompiled headers])
            AC_TRY_COMPILE([],
                [
                    #if !defined(__GNUC__) || !defined(__GNUC_MINOR__)
                        #error "no pch support"
                    #endif
                    #if (__GNUC__ < 3)
                        #error "no pch support"
                    #endif
                    #if (__GNUC__ == 3) && \
                       ((!defined(__APPLE_CC__) && (__GNUC_MINOR__ < 4)) || \
                       ( defined(__APPLE_CC__) && (__GNUC_MINOR__ < 3)))
                        #error "no pch support"
                    #endif
                ],
                [
                    AC_MSG_RESULT([yes])
                    dnl FIXME - this is temporary, till .gch dependencies 
                    dnl         are fixed in generated Makefiles
                    CPPFLAGS="-fpch-deps $CPPFLAGS"
                    GCC_PCH=1
                ],
                [
                    AC_MSG_RESULT([no])
                ])
            if test $GCC_PCH = 1 ; then
                cat <<EOF >bk-make-pch
#!/bin/sh

# This script is part of Bakefile (http://bakefile.sourceforge.net) autoconf
# script. It is used to generated precompiled headers.
#
# Permission is given to use this file in any way.

outfile="\${1}"
header="\${2}"
shift
shift

compiler=
headerfile=
while test \${#} -gt 0; do
    case "\${1}" in
        -I* )
            incdir=\`echo \${1} | sed -e 's/-I\(.*\)/\1/g'\`
            if test "x\${headerfile}" = "x" -a -f "\${incdir}/\${header}" ; then
                headerfile="\${incdir}/\${header}"
            fi
        ;;
    esac
    compiler="\${compiler} \${1}"
    shift
done

if test "x\${headerfile}" = "x" ; then
    echo "error: can't find header \${header} in include paths" >2
else
    if test -f \${outfile} ; then
        rm -f \${outfile}
    else
        mkdir -p \`dirname \${outfile}\`
    fi
    depsfile=".deps/\`basename \${outfile}\`.d"
    mkdir -p .deps
    # can do this because gcc is >= 3.4:
    \${compiler} -o \${outfile} -MMD -MF "\${depsfile}" "\${headerfile}"
    exit \${?}
fi
EOF
                chmod +x bk-make-pch
            fi
        fi
    fi

    AC_SUBST(GCC_PCH)
])



dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE
dnl
dnl To be used in configure.in of any project using Bakefile-generated mks
dnl
dnl Behaviour can be modified by setting following variables:
dnl    BAKEFILE_CHECK_BASICS    set to "no" if you don't want bakefile to
dnl                             to perform check for basic tools like ranlib
dnl    BAKEFILE_HOST            set this to override host detection, defaults
dnl                             to ${host}
dnl    BAKEFILE_FORCE_PLATFORM  set to override platform detection
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE,
[
    if test "x$BAKEFILE_HOST" = "x"; then
        BAKEFILE_HOST="${host}"
    fi

    if test "x$BAKEFILE_CHECK_BASICS" != "xno"; then
        AC_BAKEFILE_CHECK_BASIC_STUFF
    fi
    AC_BAKEFILE_GNUMAKE
    AC_BAKEFILE_PLATFORM
    AC_BAKEFILE_PLATFORM_SPECIFICS
    AC_BAKEFILE_SUFFIXES
    AC_BAKEFILE_SHARED_LD
    AC_BAKEFILE_SHARED_VERSIONS
    AC_BAKEFILE_DEPS
    AC_BAKEFILE_RES_COMPILERS

    builtin(include, autoconf_inc.m4)
])
