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
    AC_CACHE_CHECK([if make is GNU make], wx_cv_prog_makeisgnu,
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
    PLATFORM_MACOSX=0
    
    case "${host}" in
        *-*-cygwin* | *-*-mingw32* )
            PLATFORM_WIN32=1
        ;;
        *-pc-msdosdjgpp | *-pc-os2_emx | *-pc-os2-emx )
            PLATFORM_MSDOS=1
        ;;
        powerpc-*-darwin* )
            PLATFORM_MACOSX=1
        ;;
        * )
            PLATFORM_UNIX=1
        ;;
    esac

    AC_SUBST(PLATFORM_UNIX)
    AC_SUBST(PLATFORM_WIN32)
    AC_SUBST(PLATFORM_MSDOS)
    AC_SUBST(PLATFORM_MACOSX)
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
    EXEEXT=""
    DLLPREFIX=lib
    
    case "${host}" in
        *-hp-hpux* )
            SO_SUFFIX="sl"
        ;;
        *-*-aix* )
            dnl quoting from
            dnl http://www-1.ibm.com/servers/esdd/articles/gnu.html:
            dnl     Both archive libraries and shared libraries on AIX have an
            dnl     .a extension. This will explain why you can't link with an
            dnl     .so and why it works with the name changed to .a.
            SO_SUFFIX="a"
        ;;
        *-*-cygwin* | *-*-mingw32* )
            SO_SUFFIX="dll"
            EXEEXT=".exe"
            DLLPREFIX=""
        ;;
        *-pc-msdosdjgpp | *-pc-os2_emx | *-pc-os2-emx )
            EXEEXT=".exe"
            DLLPREFIX=""
        ;;
        powerpc-*-darwin* )
            SO_SUFFIX="dylib"
        ;;
    esac

    AC_SUBST(SO_SUFFIX)
    AC_SUBST(EXEEXT)
    AC_SUBST(DLLPREFIX)
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

    case "${host}" in
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
        dnl For Unix to MacOS X porting instructions, see:
        dnl http://fink.sourceforge.net/doc/porting/porting.html
        CFLAGS="$CFLAGS -fno-common"
        CXXFLAGS="$CXXFLAGS -fno-common"
        
        dnl Most apps benefit from being fully binded (its faster and static
        dnl variables initialized at startup work).
        dnl This can be done either with the exe linker flag -Wl,-bind_at_load
        dnl or with a double stage link in order to create a single module
        dnl "-init _wxWindowsDylibInit" not useful with lazy linking solved

        cat <<EOF
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

while test \$# -gt 0; do
    case \$1 in

       -v)
        verbose=1
        ;;

       -o|-compatibility_version|-current_version|-framework|-undefined|-install_name)
        # collect these options and values
        args="\$args \$1 \$2"
        shift
        ;;

       -l*|-L*|-flat_namespace)
        # collect these options
        args="\$args \$1"
        ;;

       -dynamiclib)
        # skip these options
        ;;

       -*)
        echo "shared-ld: unhandled option '\$1'"
        exit 1
        ;;

        *.o)
        # collect object files
        objects="\$objects \$1"
        ;;

        *)
        echo "shared-ld: unhandled argument '\$1'"
        exit 1
        ;;

    esac
    shift
done

#
# Link one module containing all the others
#
if test \$verbose = 1; then
    echo "c++ -r -keep_private_externs -nostdlib \$objects -o master.\$\$.o"
fi
c++ -r -keep_private_externs -nostdlib \$objects -o master.\$\$.o
status=\$?
if test \$status != 0; then
    exit \$status
fi

#
# Link the shared library from the single module created
#
if test \$verbose = 1; then
    echo "cc -dynamiclib master.\$\$.o \$args"
fi
c++ -dynamiclib master.\$\$.o \$args
status=\$?
if test \$status != 0; then
    exit \$status
fi

#
# Remove intermediate module
#
rm -f master.$$.o

exit 0
EOF >shared-ld-sh
        chmod +x shared-ld-sh

        SHARED_LD_CC="`pwd`/shared-ld-sh -undefined suppress -flat_namespace -o"
        SHARED_LD_CXX="$SHARED_LD_CC"
        PIC_FLAG="-dynamic -fPIC"
        dnl FIXME - what about C libs?
        dnl FIXME - newer devel tools have linker flag to do this, the script
        dnl         is not necessary - detect!
      ;;

      *-*-aix* )
        dnl default settings are ok for gcc
        if test "x$GCC" != "xyes"; then
            dnl the abs path below used to be hardcoded here so I guess it must
            dnl be some sort of standard location under AIX?
            AC_CHECK_PROG(AIX_CXX_LD, makeC++SharedLib,
                          makeC++SharedLib, /usr/lpp/xlC/bin/makeC++SharedLib)
            dnl FIXME - what about makeCSharedLib?            
            SHARED_LD_CC="$(AIX_CC_LD) -p 0 -o"
            SHARED_LD_CXX="$(AIX_CXX_LD) -p 0 -o"
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
      
      *-*-freebsd* | *-*-openbsd* | *-*-netbsd* | \
      *-*-sunos4* | \
      *-*-osf* | \
      *-*-dgux5* | \
      *-*-sysv5* )
        dnl defaults are ok
      ;;

      *)
        AC_MSG_ERROR(unknown system type $host.)
    esac

    AC_SUBST(SHARED_LD_CC)
    AC_SUBST(SHARED_LD_CXX)
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

    case "${host}" in
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
        dnl library installation base name and wxMac resources file base name
        dnl must be identical in order for the resource file to be found at
        dnl run time in src/mac/app.cpp
        SONAME_FLAG="-compatibility_version ${WX_RELEASE} -current_version ${WX_VERSION} -install_name \$(libdir)/${WX_LIBRARY_LINK1}"
        dnl FIXME -- broken
        USE_MACVERSION=1
        USE_SOVERSION=1
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
    DEPS_TYPE=no
    if test "x$GCC" = "xyes"; then
        DEPS_TYPE=gcc
    fi
    
    AC_SUBST(DEPS_TYPE)
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
    
    if test "$build" != "$host" ; then
        AR=$host_alias-ar
        STRIP=$host_alias-strip
    else
        AC_CHECK_PROG(AR, ar, ar, ar)
        AC_CHECK_PROG(STRIP, strip, strip, true)
    fi

    case ${host} in
        *-hp-hpux* )
            INSTALL_DIR="mkdir"
            ;;
        *)  INSTALL_DIR="$INSTALL -d"
            ;;
    esac
    AC_SUBST(INSTALL_DIR)

    dnl Check for win32 resources compiler:
    case ${host} in 
        *-*-cygwin* | *-*-mingw32* )
            if test "$build" != "$host" ; then
                WINDRES=$host_alias-windres
            else
                AC_CHECK_PROG(WINDRES, windres, windres, windres)
            fi
            ;;
        *)  
            WINDRES=
            ;;
    esac
    AC_SUBST(WINDRES)
])

dnl ---------------------------------------------------------------------------
dnl AC_BAKEFILE
dnl
dnl To be used in configure.in of any project using BAKEFILE-generated makefiles.
dnl ---------------------------------------------------------------------------

AC_DEFUN(AC_BAKEFILE,
[
    if test "x$BAKEFILE_CHECK_BASICS" != "xno"; then
        AC_BAKEFILE_CHECK_BASIC_STUFF
    fi
    AC_BAKEFILE_GNUMAKE
    AC_BAKEFILE_PLATFORM
    AC_BAKEFILE_SUFFIXES
    AC_BAKEFILE_SHARED_LD
    AC_BAKEFILE_SHARED_VERSIONS
    AC_BAKEFILE_DEPS

    builtin(include, autoconf_inc.m4)
])
