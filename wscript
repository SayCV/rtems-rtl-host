#
# RTEMS Linker build script.
#
import sys

version_major = 1
version_minor = 0
version_revision = 0

#
# Waf system setup. Allow more than one build in the same tree.
#
top = '.'
out = 'build-' + sys.platform

def options(opt):
    opt.load("g++")
    opt.load("gcc")
    opt.add_option('--rtems-version',
                   default = '4.11',
                   dest='rtems_version',
                   help = 'Set the RTEMS version')
    opt.add_option('--c-opts',
                   default = '-O2',
                   dest='c_opts',
                   help = 'Set build options, default: -O2.')
    opt.add_option('--show-commands',
                   action = 'store_true',
                   default = False,
                   dest = 'show_commands',
                   help = 'Print the commands as strings.')

def configure(conf):
    try:
        conf.load("doxygen", tooldir = 'waf-tools')
    except:
        pass
    conf.load("g++")
    conf.load("gcc")
    conf_libiberty(conf)
    conf_libelf(conf)

    conf.check(header_name='sys/wait.h',  features = 'c', mandatory = False)
    conf.check_cc(function_name='kill', header_name="signal.h",
                  features = 'c', mandatory = False)
    conf.write_config_header('config.h')

    conf.env.C_OPTS = conf.options.c_opts.split(',')
    conf.env.RTEMS_VERSION = conf.options.rtems_version

    if conf.options.show_commands:
        show_commands = 'yes'
    else:
        show_commands = 'no'
    conf.env.SHOW_COMMANDS = show_commands

def build(bld):
    from waflib import Utils, Logs
    
    #
    # Build the doxygen documentation.
    #
    if bld.cmd == 'doxy':
        bld(features = 'doxygen',
            doxyfile = 'rtl-host.conf')
        return

    if bld.env.SHOW_COMMANDS == 'yes':
        output_command_line()

    #
    # The include paths.
    #
    bld.includes = ['elftoolchain/libelf', 'elftoolchain/common', 'libiberty']
    if sys.platform == 'win32':
        bld.includes += ['win32']
    if sys.platform == 'cygwin2':
        bld.includes += ['win32']
    
    #
    # Build flags.
    #
    bld.warningflags = ['-Wall', '-Wextra', '-pedantic']
    bld.optflags = bld.env.C_OPTS
    bld.cflags = ['-pipe', '-g'] + bld.optflags
    bld.cxxflags = ['-pipe', '-g'] + bld.optflags
    bld.linkflags = ['-g']
    
    if sys.platform == 'cygwin':
        bld.cflags += ['-D__WIN32__']
        bld.cxxflags += ['-D__WIN32__']
        bld.linkflags += ['-D__WIN32__']
    
    #Logs.info('%s' % bld.cflags)
    #
    # Create each of the modules as object files each with their own
    # configurations.
    #
    bld_fastlz(bld)
    bld_libelf(bld)
    bld_libiberty(bld)

    #
    # The list of modules.
    #
    modules = ['fastlz', 'elf', 'iberty']

    #
    # RLD source.
    #
    rld_source = ['rld-elf.cpp',
                  'rld-files.cpp',
                  'rld-cc.cpp',
                  'rld-compression.cpp',
                  'rld-outputter.cpp',
                  'rld-process.cpp',
                  'rld-resolver.cpp',
                  'rld-symbols.cpp',
                  'rld-rap.cpp',
                  'rld.cpp']

    #
    # RTEMS Utilities.
    #
    rtems_utils = ['rtems-utils.cpp']
    
    #
    # Build the linker.
    #
    bld.program(target = 'rtems-ld',
                source = ['rtems-ld.cpp',
                          'pkgconfig.cpp'] + rld_source,
                defines = ['HAVE_CONFIG_H=1', 'RTEMS_VERSION=' + bld.env.RTEMS_VERSION],
                includes = ['.'] + bld.includes,
                cflags = bld.cflags + bld.warningflags,
                cxxflags = bld.cxxflags + bld.warningflags,
                linkflags = bld.linkflags,
                use = modules)

    #
    # Build the symbols.
    #
    bld.program(target = 'rtems-syms',
                source = ['rtems-syms.cpp'] + rld_source,
                defines = ['HAVE_CONFIG_H=1', 'RTEMS_VERSION=' + bld.env.RTEMS_VERSION],
                includes = ['.'] + bld.includes,
                cflags = bld.cflags + bld.warningflags,
                cxxflags = bld.cxxflags + bld.warningflags,
                linkflags = bld.linkflags,
                use = modules)

    #
    # Build the RAP utility.
    #
    bld.program(target = 'rtems-rap',
                source = ['rtems-rapper.cpp'] + rld_source + rtems_utils,
                defines = ['HAVE_CONFIG_H=1', 'RTEMS_VERSION=' + bld.env.RTEMS_VERSION],
                includes = ['.'] + bld.includes,
                cflags = bld.cflags + bld.warningflags,
                cxxflags = bld.cxxflags + bld.warningflags,
                linkflags = bld.linkflags,
                use = modules)

def rebuild(ctx):
    import waflib.Options
    waflib.Options.commands.extend(['clean', 'build'])

def tags(ctx):
    ctx.exec_command('etags $(find . -name \*.[sSch])', shell = True)

#
# Libelf module.
#
def conf_libelf(conf):
    pass

def bld_fastlz(bld):
    bld(target = 'fastlz',
        features = 'c',
        source = 'fastlz.c',
        cflags = bld.cflags,
        defines = ['FASTLZ_LEVEL=1'])

def bld_libelf(bld):
    from waflib import Utils, Logs
    libelf = 'elftoolchain/libelf/'

    #
    # Work around the ${SRC} having Windows slashes which the MSYS m4 does not
    # understand.
    #
    if sys.platform == 'win32':
        m4_rule = 'type ${SRC} | m4 -D SRCDIR=../' + libelf[:-1] + '> ${TGT}"'
        includes = ['win32']
    if sys.platform == 'cygwin2':
        m4_rule = 'm4 -D SRCDIR=../' + libelf[:-1] + ' ${SRC} > ${TGT}'
        includes = ['win32']
    else:
        m4_rule = 'm4 -D SRCDIR=../' + libelf[:-1] + ' ${SRC} > ${TGT}'
        includes = []

    bld(target = 'libelf_convert.c', source = libelf + 'libelf_convert.m4', rule = m4_rule)
    bld(target = 'libelf_fsize.c',   source = libelf + 'libelf_fsize.m4',   rule = m4_rule)
    bld(target = 'libelf_msize.c',   source = libelf + 'libelf_msize.m4',   rule = m4_rule)

    host_source = []

    if sys.platform == 'linux2':
        common = 'elftoolchain/common/'
        bld(target = common + 'native-elf-format.h',
            source = common + 'native-elf-format',
            name = 'native-elf-format',
            rule   = './${SRC} > ${TGT}')
        bld.add_group ()
    elif sys.platform == 'win32':
        host_source += [libelf + 'mmap_win32.c']
    elif sys.platform == 'cygwin':
        host_source += [libelf + 'mmap_win32.c']

    bld.stlib(target = 'elf',
              features = 'c',
              uses = ['native-elf-format'],
              includes = [bld.bldnode.abspath(), 'elftoolchain/libelf', 'elftoolchain/common'] + includes,
              cflags = bld.cflags,
              source =[libelf + 'elf.c',
                       libelf + 'elf_begin.c',
                       libelf + 'elf_cntl.c',
                       libelf + 'elf_end.c',
                       libelf + 'elf_errmsg.c',
                       libelf + 'elf_errno.c',
                       libelf + 'elf_data.c',
                       libelf + 'elf_fill.c',
                       libelf + 'elf_flag.c',
                       libelf + 'elf_getarhdr.c',
                       libelf + 'elf_getarsym.c',
                       libelf + 'elf_getbase.c',
                       libelf + 'elf_getident.c',
                       libelf + 'elf_hash.c',
                       libelf + 'elf_kind.c',
                       libelf + 'elf_memory.c',
                       libelf + 'elf_next.c',
                       libelf + 'elf_rand.c',
                       libelf + 'elf_rawfile.c',
                       libelf + 'elf_phnum.c',
                       libelf + 'elf_shnum.c',
                       libelf + 'elf_shstrndx.c',
                       libelf + 'elf_scn.c',
                       libelf + 'elf_strptr.c',
                       libelf + 'elf_update.c',
                       libelf + 'elf_version.c',
                       libelf + 'gelf_cap.c',
                       libelf + 'gelf_checksum.c',
                       libelf + 'gelf_dyn.c',
                       libelf + 'gelf_ehdr.c',
                       libelf + 'gelf_getclass.c',
                       libelf + 'gelf_fsize.c',
                       libelf + 'gelf_move.c',
                       libelf + 'gelf_phdr.c',
                       libelf + 'gelf_rel.c',
                       libelf + 'gelf_rela.c',
                       libelf + 'gelf_shdr.c',
                       libelf + 'gelf_sym.c',
                       libelf + 'gelf_syminfo.c',
                       libelf + 'gelf_symshndx.c',
                       libelf + 'gelf_xlate.c',
                       libelf + 'libelf_align.c',
                       libelf + 'libelf_allocate.c',
                       libelf + 'libelf_ar.c',
                       libelf + 'libelf_ar_util.c',
                       libelf + 'libelf_checksum.c',
                       libelf + 'libelf_data.c',
                       libelf + 'libelf_ehdr.c',
                       libelf + 'libelf_extended.c',
                       libelf + 'libelf_phdr.c',
                       libelf + 'libelf_shdr.c',
                       libelf + 'libelf_xlate.c',
                       'libelf_convert.c',
                       'libelf_fsize.c',
                       'libelf_msize.c'] + host_source)

#
# Libiberty module.
#
def conf_libiberty(conf):
    conf.check(header_name='alloca.h',    features = 'c', mandatory = False)
    conf.check(header_name='fcntl.h',     features = 'c', mandatory = False)
    conf.check(header_name='process.h',   features = 'c', mandatory = False)
    conf.check(header_name='stdlib.h',    features = 'c')
    conf.check(header_name='string.h',    features = 'c')
    conf.check(header_name='strings.h',   features = 'c', mandatory = False)
    conf.check(header_name='sys/file.h',  features = 'c', mandatory = False)
    conf.check(header_name='sys/stat.h',  features = 'c', mandatory = False)
    conf.check(header_name='sys/time.h',  features = 'c', mandatory = False)
    conf.check(header_name='sys/types.h', features = 'c', mandatory = False)
    conf.check(header_name='sys/wait.h',  features = 'c', mandatory = False)
    conf.check(header_name='unistd.h',    features = 'c', mandatory = False)
    conf.check(header_name='vfork.h',     features = 'c', mandatory = False)

    conf.check_cc(function_name='getrusage',
                  header_name="sys/time.h sys/resource.h",
                  features = 'c', mandatory = False)

    conf.write_config_header('libiberty/config.h')

def bld_libiberty(bld):
    if sys.platform == 'win32':
        pex_host = 'libiberty/pex-win32.c'
    elif sys.platform == 'cygwin2':
        pex_host = 'libiberty/pex-win32.c'
    else:
        pex_host = 'libiberty/pex-unix.c'
    bld.stlib(target = 'iberty',
              features = 'c',
              includes = ['libiberty'],
              cflags = bld.cflags,
              defines = ['HAVE_CONFIG_H=1'],
              source =['libiberty/concat.c',
                       'libiberty/cplus-dem.c',
                       'libiberty/cp-demangle.c',
                       'libiberty/make-temp-file.c',
                       'libiberty/mkstemps.c',
                       'libiberty/safe-ctype.c',
                       'libiberty/stpcpy.c',
                       'libiberty/pex-common.c',
                       'libiberty/pex-one.c',
                       pex_host])

#
# From the demos. Use this to get the command to cut+paste to play.
#
def output_command_line():
    # first, display strings, people like them
    from waflib import Utils, Logs
    from waflib.Context import Context
    def exec_command(self, cmd, **kw):
        subprocess = Utils.subprocess
        kw['shell'] = isinstance(cmd, str)
        if isinstance(cmd, str):
            Logs.info('%s' % cmd)
        else:
            Logs.info('%s' % ' '.join(cmd)) # here is the change
        Logs.debug('runner_env: kw=%s' % kw)
        try:
            if self.logger:
                self.logger.info(cmd)
                kw['stdout'] = kw['stderr'] = subprocess.PIPE
                p = subprocess.Popen(cmd, **kw)
                (out, err) = p.communicate()
                if out:
                    self.logger.debug('out: %s' % out.decode(sys.stdout.encoding or 'iso8859-1'))
                if err:
                    self.logger.error('err: %s' % err.decode(sys.stdout.encoding or 'iso8859-1'))
                return p.returncode
            else:
                p = subprocess.Popen(cmd, **kw)
                return p.wait()
        except OSError:
            return -1
    Context.exec_command = exec_command

    # Change the outputs for tasks too
    from waflib.Task import Task
    def display(self):
        return '' # no output on empty strings

    Task.__str__ = display

#
# The doxy command.
#
from waflib import Build
class doxy(Build.BuildContext):
    fun = 'build'
    cmd = 'doxy'
