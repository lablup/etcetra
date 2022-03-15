#! /usr/bin/env python

import argparse
import re
import subprocess
import glob
from pathlib import Path
import random
import shutil
import string
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
        (tmp_dst / 'gogoproto').mkdir()
        shutil.copytree(googleapis_root / 'google', tmp_dst / 'google')
        shutil.copy(
            gogoproto_root / 'gogoproto' / 'gogo.proto',
            tmp_dst / 'gogoproto' / 'gogo.proto',
        )

        exec_command(['chmod', '-R', '755', tmp_dst.as_posix()])

        protos_to_compile: List[Path] = [tmp_dst / 'gogoproto' / 'gogo.proto']
        for google_protobuf in glob.glob(
            (tmp_dst / 'google').as_posix() + '/**/*.proto',
            recursive=True,
        ):
            protos_to_compile.append(Path(google_protobuf))

        search_directories = list(glob.glob((repo_path / 'api' / '*pb').as_posix()))
        search_directories += list(
            glob.glob((repo_path / 'server' / 'etcdserver' / 'api' / '**' / '*pb').as_posix()),
        )
        for raw_subdir in search_directories:
            subdir = Path(raw_subdir).resolve()
            if not subdir.is_dir() and not subdir.name.endswith('pb'):
                continue
            (tmp_dst / subdir.name).mkdir()
            (tmp_dst / subdir.name / '__init__.py').touch()

            for raw_protobuf_file in glob.glob(raw_subdir + '/*.proto'):
                protobuf_file = Path(raw_protobuf_file).resolve()
                protos_to_compile.append(tmp_dst / subdir.name / protobuf_file.name)

                with open(protobuf_file, 'r') as fr:
                    modified_protobuf = ''
                    for line in fr.readlines():
                        if line.startswith('import "etcd/api'):
                            modified_protobuf += line.replace('import "etcd/api/', 'import "')
                        else:
                            modified_protobuf += line
                with open(tmp_dst / subdir.name / protobuf_file.name, 'w') as fw:
                    fw.write(modified_protobuf)

        SAME_PACKAGE_IMPORT = re.compile(r'^import ([^_]+)_pb2')
        RELATIVE_IMPORT = re.compile(r'^from ([^ ]+)pb import ([^_]+)_pb2')

        for proto in protos_to_compile:
            build_proto(
                proto,
                proto.parent,
                [tmp_dst],
            )
            proto_name = proto.name.rsplit('.', 1)[0]
            proto_filename = proto.as_posix().replace(tmp_dst.as_posix() + '/', '')
            base_pkg = 'from etcetra.grpc_api'
            for python_file in [proto_name + '_pb2.py', proto_name + '_pb2_grpc.py']:
                print('updating:', python_file)
                with open(proto.parent / python_file, 'r') as fr:
                    replaced_script = ''
                    for line in fr.readlines():
                        if line.startswith('from gogoproto'):
                            replaced_line = line.replace('from gogoproto', f'{base_pkg}.gogoproto')
                        elif line.startswith('from google.api'):
                            replaced_line = line.replace('from google.api', f'{base_pkg}.google.api')
                        elif matched := RELATIVE_IMPORT.match(line):
                            package, file = matched.groups()
                            replaced_line = f'{base_pkg}.{package}pb import {file}_pb2 as {file}__pb2\n'
                        elif matched := SAME_PACKAGE_IMPORT.match(line):
                            filename = matched.groups()[0]
                            replaced_line = f'from . import {filename}_pb2 as {filename}__pb2\n'
                        elif line.startswith('DESCRIPTOR = '):
                            replaced_line = line
                            # FIXME: Manually included line below crashes when Protobuf API backend
                            # is `cpp` instead of `python`. We should find out more generalized way
                            # which supports both `cpp` and `python` mode and apply.
                            replaced_line += ('_descriptor_pool.Default()._internal_db.'
                                              f'_file_desc_protos_by_file[\'{proto_filename}\']'
                                              ' = DESCRIPTOR')
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
        shutil.rmtree(tmp_dst)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('version', type=str, help='target etcd version')
    parser.add_argument(
        '--repository-path', type=str,
        help='git repository folder path of etcd source code to use. Ff not supplied, '
             'this script will clone fresh repo on temporary directory and remove it upon exit.')
    args = parser.parse_args()

    main(args.version, Path(args.repository_path).resolve())
