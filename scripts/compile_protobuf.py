#! /usr/bin/env python

import argparse
import re
import glob
import tempfile
from pathlib import Path
import random
import shutil
import string
import subprocess
from typing import List, Optional


def exec_command(
    command: List[str],
    cwd: Optional[Path] = None,
    capture_stdout: Optional[bool] = False,
    capture_stderr: Optional[bool] = False,
):
    print('executing:', *command)
    proc = subprocess.Popen(
        ['/usr/bin/env'] + command, cwd=cwd,
        stdout=subprocess.PIPE if capture_stdout else None,
        stderr=subprocess.PIPE if capture_stderr else None,
    )
    out, err = proc.communicate()
    if proc.returncode != 0:
        # print(err.decode('utf-8'))
        exit(-1)
    return out, err


def resolve_gopkg_dir(repo_path: Path, library: str):
    out, _ = exec_command(
        ['go', 'list', '-f', '{{.Dir}}',  library],
        cwd=repo_path / 'tools' / 'mod', capture_stdout=True,
    )
    return (Path(out.decode('utf-8')) / '..').resolve()


def build_proto(infile: Path, outdir: Path, includes: List[Path]):
    arguments = ['python', '-m', 'grpc_tools.protoc']
    arguments.append('-I=' + infile.parent.as_posix())
    for include in includes:
        arguments.append('-I=' + include.as_posix())
    arguments.append('--grpc_python_out=' + outdir.as_posix())
    arguments.append('--python_out=' + outdir.as_posix())
    arguments.append(infile.as_posix())
    exec_command(arguments, cwd=infile.parent)


def main(version: str, repo_path: Optional[Path] = None):
    folder_name = 'etcd-repo-' + ''.join(random.sample(string.ascii_letters, 8))
    did_clone = False
    if repo_path is None:
        did_clone = True
        repo_path = Path('/tmp') / folder_name
        exec_command(
            ['git', 'clone', 'https://github.com/etcd-io/etcd', folder_name],
            Path('/tmp'),
        )

    tmp_dst = Path('/tmp') / ('etcd-gen-' + ''.join(random.sample(string.ascii_letters, 8)))
    tmp_dst.mkdir()
    try:
        exec_command(['git', 'checkout', version], repo_path)
        exec_command(['go', 'get', '-v'], repo_path)

        # resolve dependency path
        grpc_gw_root = resolve_gopkg_dir(
            repo_path, 'github.com/grpc-ecosystem/grpc-gateway/protoc-gen-grpc-gateway')
        googleapis_root = grpc_gw_root / 'third_party' / 'googleapis'
        gogoproto_root = resolve_gopkg_dir(repo_path, 'github.com/gogo/protobuf/proto')
        package_root = (
            Path(__file__).parent / '..' / 'src' / 'etcetra' / 'grpc_api'
        )
        package_root = package_root.resolve()

        if package_root.is_dir():
            shutil.rmtree(package_root)
        package_root.parent.mkdir(parents=True, exist_ok=True)

        # copy dependency protobufs

        exec_command(['chmod', '-R', '755', tmp_dst.as_posix()])

        search_directories = [
            repo_path / 'server' / 'etcdserver' / 'api',
            repo_path / 'api' / '*pb',
            googleapis_root / 'google',
            gogoproto_root / 'gogoproto',
        ]
        packages: List[str] = ['gogoproto', 'google/http', 'google/api']
        for subdir in glob.glob((repo_path / 'api' / '*pb').as_posix()):
            packages.append('etcd/api/' + Path(subdir).name)
        print('packages:', packages)
        protos_to_compile: List[str] = []
        for raw_subdir in search_directories:
            for raw_protobuf_file in glob.glob(
                (raw_subdir / '**' / '*.proto').as_posix(), recursive=True,
            ):
                protobuf_file = Path(raw_protobuf_file).resolve()

                with open(protobuf_file, 'r') as fr:
                    modified_protobuf = ''
                    for line in fr.readlines():
                        for package in packages:
                            if line.startswith(f'import "{package}/'):
                                print(':matched', package)
                                modified_protobuf += line.replace(f'import "{package}/', 'import "')
                                break
                        else:
                            modified_protobuf += line
                with open(tmp_dst / protobuf_file.name, 'w') as fw:
                    fw.write(modified_protobuf)
                protos_to_compile.append(tmp_dst / protobuf_file.name)

        SAME_PACKAGE_IMPORT = re.compile(r'^import ([^_]+)_pb2')
        RELATIVE_IMPORT = re.compile(r'^from ([^ ]+)pb import ([^_]+)_pb2')

        for proto in protos_to_compile:
            build_proto(
                proto,
                proto.parent,
                [],
            )
            proto_name = proto.name.rsplit('.', 1)[0]
            base_pkg = 'from etcetra.grpc_api'
            for python_file in [proto_name + '_pb2.py', proto_name + '_pb2_grpc.py']:
                print('updating:', python_file)
                with open(proto.parent / python_file, 'r') as fr:
                    replaced_script = ''
                    for line in fr.readlines():
                        if line.startswith('from gogoproto'):
                            replaced_line = line.replace('from gogoproto', f'{base_pkg}')
                        elif line.startswith('from google.api'):
                            replaced_line = line.replace('from google.api', f'{base_pkg}')
                        elif matched := RELATIVE_IMPORT.match(line):
                            package, file = matched.groups()
                            replaced_line = f'{base_pkg} import {file}_pb2 as {file}__pb2\n'
                        elif matched := SAME_PACKAGE_IMPORT.match(line):
                            filename = matched.groups()[0]
                            replaced_line = f'{base_pkg} import {filename}_pb2 as {filename}__pb2\n'
                        elif line.startswith('DESCRIPTOR = '):
                            replaced_line = line
                        else:
                            replaced_line = line
                        replaced_script += replaced_line
                with open(proto.parent / python_file, 'w') as fw:
                    fw.write(replaced_script)

        with open(tmp_dst / '__init__.py', 'w') as fw:
            fw.write(f'ETCD_VERSION = \'{version}\'\n')

        shutil.copytree(tmp_dst, package_root)
    finally:
        if did_clone:
            shutil.rmtree(repo_path)
        # shutil.rmtree(tmp_dst)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('version', type=str, help='target etcd version')
    parser.add_argument(
        '--repository-path', type=str,
        help='git repository folder path of etcd source code to use. If not supplied, '
             'this script will clone fresh repo on temporary directory and remove it upon exit.')
    args = parser.parse_args()
    if (_path := args.repository_path) is not None:
        repo_path = Path(_path)
    else:
        repo_path = None

    main(args.version, repo_path)
