import argparse
import subprocess
import os
import shutil
import re
from datetime import datetime
import zipfile

class CommandError(Exception):
    pass

def run_command(command):
    print('Execute command: "%s"...' % ' '.join(command))
    s = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = s.communicate()
    def write_logs(out, err):
        out = out.decode("utf-8")
        err = err.decode("utf-8")
        stdout_log = str(s.pid) + "_stdout.log"
        stderr_log = str(s.pid) + "_stderr.log"
        with open(stdout_log, "w") as f:
            f.write(out)
        with open(stderr_log, "w") as f:
            f.write(err)
        print(f"Output log files: {stdout_log}, {stderr_log}")
        
    if s.returncode != 0:
        print('failed')
        write_logs(out, err)
        raise RuntimeError(f"Command failed: {command}. Exitcode: {s.returncode}")

def file_exists(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False
    return True

def extract_match(regex, text):
    match = re.search(regex, text)
    if not match:
        raise AssertionError(f'Failed to match pattern: {pattern} with regex: {regex}')
    return match.group(1)

def display_info(info_dict):
    print('================================')
    for key, value in info_dict.items():
        print(f"{key}={value}")
    print('================================')

def create_zip(zip_filename, files):
    print(f"Creating zip: {zip_filename} with {len(files)} files")
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for file in files:
            zf.write(file)
    print("Zip creation complete")

def match_and_get(regex: str, pattern: str):
    matched = re.search(regex, pattern)
    if not matched:
        raise AssertionError('Failed to match: for pattern: %s regex: %s' % pattern, regex)
    return matched.group(1)


class ClangCompiler:
    @staticmethod
    def verify_executable():
        try:
            run_command(['./toolchain/bin/clang', '-v'])
        except RuntimeError as e:
            print("Failed to execute clang, something went wrong")
            raise e
    
    @staticmethod
    def get_version():
        clangversionRegex = r"(.*?clang version \d+(\.\d+)*).*"
        s = subprocess.Popen(['./toolchain/bin/clang', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, tcversion = s.communicate()
        tcversion = tcversion.decode('utf-8')
        return match_and_get(clangversionRegex, tcversion)
    

def main():
    parser = argparse.ArgumentParser(description="Build Kernel with specified arguments")
    parser.add_argument('--target', type=str, required=True, help="Target device (a51/m21/...)")
    parser.add_argument('--allow-dirty', action='store_true', help="Allow dirty build")
    parser.add_argument('--oneui', action='store_true', help="OneUI build")
    args = parser.parse_args()
    
    valid_targets = ['a51', 'f41', 'm31s', 'm31', 'm21', 'gta4xl', 'gta4xlwifi']
    if args.target not in valid_targets:
        print("Specify a valid target: a51/f41/m31s/m31/m21/gta4xl/gta4xlwifi")
        return

    common_flags = [
        'CROSS_COMPILE=aarch64-linux-gnu-', 'CC=clang', 'LD=ld.lld', 
        'AS=llvm-as', 'AR=llvm-ar', 'OBJDUMP=llvm-objdump', 
        'READELF=llvm-readelf', 'NM=llvm-nm', 'OBJCOPY=llvm-objcopy', 
        'ARCH=arm64', f'-j{os.cpu_count()}'
    ]
 
    kernel_version = "1.6.0"

    if not file_exists("AnyKernel3/anykernel.sh"):
        run_command(['git', 'submodule', 'update', '--init'])
    if not file_exists("toolchain/bin/clang"):
        print(f"Toolchain must be available at {os.getcwd()}/toolchain")
        return
    
    ClangCompiler.verify_executable()
    
    build_type = "OneUI" if args.oneui else "AOSP"
    display_info({
        'Kernel Name': 'Something New',
        'Kernel Version': kernel_version,
        'Build Type': build_type,
        'Device': args.target,
        'TARGET_USES_LLVM': True,
        'TOOLCHAIN_VERSION': ClangCompiler.get_version(),
    })
    
    toolchain_path = os.path.join(os.getcwd(), 'toolchain', 'bin')
    if toolchain_path not in os.environ['PATH'].split(os.pathsep):
        os.environ["PATH"] = toolchain_path + ':' + os.environ["PATH"]
    
    output_dir = 'out'
    if os.path.exists(output_dir) and not args.allow_dirty:
        print('Cleaning build output...')
        shutil.rmtree(output_dir)
    
    make_common = ['make', 'O=out', 'LLVM=1', f'-j{os.cpu_count()}'] + common_flags
    make_defconfig = make_common + [f'exynos9611-{args.target}_defconfig']
#    make_nethunter = make_common + ["nethunter_defconfig"]

    if args.oneui:
        make_defconfig += ['oneui.config']
    
    start_time = datetime.now()
    print('Running make defconfig...')
    run_command(make_defconfig)
#    print("Running defconfig for NetHunter...")
#    run_command(make_nethunter)
    print('Building the kernel...')
    run_command(make_common)
    print('Build complete')
    elapsed_time = datetime.now() - start_time
    
    with open(os.path.join(output_dir, 'include', 'generated', 'utsrelease.h')) as f:
        kernel_version_info = extract_match(r'"([^"]+)"', f.read())
    
    shutil.copyfile('out/arch/arm64/boot/Image', 'AnyKernel3/Image')
    zip_filename = 'SN_{}_{}_{}_{}.zip'.format(
        kernel_version, args.target, 'OneUI' if args.oneui else 'AOSP', datetime.today().strftime('%Y-%m-%d'))
    os.chdir('AnyKernel3/')
    create_zip(zip_filename, [
        'Image', 
        'META-INF/com/google/android/update-binary',
        'META-INF/com/google/android/updater-script',
        'tools/ak3-core.sh',
        'tools/busybox',
        'tools/magiskboot',
        'anykernel.sh',
        'version'
    ])
    final_zip_path = os.path.join(os.getcwd(), '..', zip_filename)
    try:
        os.remove(final_zip_path)
    except FileNotFoundError:
        pass
    shutil.move(zip_filename, final_zip_path)
    os.chdir('..')
    display_info({
        'OUT_ZIPNAME': zip_filename,
        'KERNEL_VERSION': kernel_version_info,
        'ELAPSED_TIME': f"{elapsed_time.total_seconds()} seconds"
    })
    
if __name__ == '__main__':
    main()

