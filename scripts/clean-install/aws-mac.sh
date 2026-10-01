#!/usr/bin/env bash
# Host-side driver for the macOS clean-install harness on an EC2 Mac
# (mac2.metal dedicated host). See the coga/testing/clean-install/macos-aws topic.
set -Eeuo pipefail
umask 077

usage() {
    cat >&2 <<'EOF'
usage (export AWS_PROFILE first; every aws call passes it):
  aws-mac.sh preflight REGION
  aws-mac.sh provision NAME REGION AZ     (COGA_CLEAN_INSTALL_ALLOCATE=yes)
  aws-mac.sh walk NAME pypi|main MAC_USER [OPERATOR]
  aws-mac.sh ssh NAME [REMOTE-COMMAND ...]
  aws-mac.sh vnc NAME
  aws-mac.sh status NAME
  aws-mac.sh teardown NAME
  aws-mac.sh release NAME
EOF
    exit 2
}

[[ $# -ge 2 ]] || usage
command=$1
shift
if [[ -z ${AWS_PROFILE:-} ]]; then
    echo "Export AWS_PROFILE (after aws sso login --profile <profile>)" >&2
    exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(git -C "$script_dir" rev-parse --show-toplevel)
region=

run() {
    # Trace to stderr so a command's own stdout can be captured cleanly.
    {
        printf '\n+'
        printf ' %q' "$@"
        printf '\n'
    } >&2
    "$@"
}

awsc() {
    aws --profile "$AWS_PROFILE" --region "$region" "$@"
}

record() {
    # Every resource ID is written the moment it exists, so teardown can find
    # everything a failed provision left behind.
    printf '%s=%q\n' "$1" "$2" >> "$evidence/resources.env"
    printf -v "$1" '%s' "$2"
    printf 'recorded %s=%s\n' "$1" "$2"
}

record_output() {
    # Capture separately: record KEY "$(aws ...)" would hide the AWS exit code.
    local key=$1 value
    shift
    value=$("$@")
    record "$key" "$value"
}

checksum() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi
}

load() {
    local name=$1
    if [[ ! $name =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
        echo "NAME must be lowercase letters, digits and dashes" >&2
        exit 2
    fi
    evidence="$repo_root/.coga/clean-install/$name"
    resource_name="coga-clean-install-$name"
    if [[ $command != provision ]]; then
        if [[ ! -f $evidence/resources.env ]]; then
            echo "No provisioned run named $name ($evidence/resources.env)" >&2
            exit 2
        fi
        # shellcheck disable=SC1091
        source "$evidence/resources.env"
        region=$REGION
        # An interactive ssh session keeps its terminal; everything else is logged.
        [[ $command == ssh ]] && return
        exec > >(tee -a "$evidence/host.txt") 2>&1
        printf '\n=== %s %s %s\n' "$(date -u +%FT%TZ)" "$command" "$name"
    fi
}

ssh_args() {
    ssh_opts=(-i "$evidence/key.pem" -o IdentitiesOnly=yes
        -o StrictHostKeyChecking=accept-new
        -o UserKnownHostsFile="$evidence/known_hosts" -o ConnectTimeout=15)
    target="ec2-user@$PUBLIC_IP"
}

mac() {
    ssh "${ssh_opts[@]}" "$target" "$@"
}

latest_ami() {
    awsc ec2 describe-images --owners amazon \
        --filters 'Name=name,Values=amzn-ec2-macos-*' Name=architecture,Values=arm64_mac \
        --query 'sort_by(Images,&CreationDate)[-1].[ImageId,Name]' --output text
}

preflight() {
    [[ $# -eq 1 ]] || usage
    region=$1
    run awsc sts get-caller-identity --query Arn --output text
    echo 'mac2 dedicated-host quotas:'
    awsc service-quotas list-service-quotas --service-code ec2 \
        --query "Quotas[?contains(QuotaName, 'mac2')].[QuotaName,Value]" --output text
    echo 'Availability zones offering mac2.metal:'
    awsc ec2 describe-instance-type-offerings --location-type availability-zone \
        --filters Name=instance-type,Values=mac2.metal \
        --query 'InstanceTypeOfferings[].Location' --output text
    echo 'Existing mac2.metal hosts:'
    awsc ec2 describe-hosts --filter Name=instance-type,Values=mac2.metal \
        --query 'Hosts[].[HostId,State,AvailabilityZone,AllocationTime]' --output text
    echo 'Newest arm64 macOS AMI:'
    latest_ami
}

provision() {
    [[ $# -eq 3 ]] || usage
    load "$1"
    region=$2
    local az=$3
    if [[ ${COGA_CLEAN_INSTALL_ALLOCATE:-} != yes ]]; then
        cat >&2 <<'EOF'
Refusing to allocate: a mac2.metal dedicated host bills for at least 24 hours
and cannot be released sooner. Get the owner's approval of the region and cost,
then rerun with COGA_CLEAN_INSTALL_ALLOCATE=yes.
EOF
        exit 2
    fi
    if [[ -e $evidence ]]; then
        echo "Evidence already exists: $evidence; choose a new NAME" >&2
        exit 2
    fi
    mkdir -p "$evidence"
    exec > >(tee -a "$evidence/host.txt") 2>&1
    run_name=$1
    trap 'status=$?; printf "FAILED (exit %s): %s\nResources so far are in %s; run: %q teardown %q\n" "$status" "$BASH_COMMAND" "$evidence/resources.env" "$0" "$run_name" >&2; exit "$status"' ERR
    record REGION "$region"
    record AZ "$az"
    record_output CALLER awsc sts get-caller-identity --query Arn --output text

    local ami ami_name subnet vpc ip
    if [[ -n ${COGA_MAC_AMI:-} ]]; then
        ami=$COGA_MAC_AMI
        ami_name=$(awsc ec2 describe-images --image-ids "$ami" --query 'Images[0].Name' --output text)
    else
        read -r ami ami_name < <(latest_ami)
    fi
    [[ $ami == ami-* ]] || { echo "No macOS AMI found in $region" >&2; false; }
    record AMI "$ami"
    record AMI_NAME "$ami_name"
    read -r subnet vpc < <(awsc ec2 describe-subnets \
        --filters "Name=availability-zone,Values=$az" Name=default-for-az,Values=true \
        --query 'Subnets[0].[SubnetId,VpcId]' --output text)
    [[ $subnet == subnet-* ]] || { echo "No default subnet in $az" >&2; false; }
    ip=$(curl -fsS https://checkip.amazonaws.com)
    record SSH_FROM "$ip/32"

    run awsc ec2 create-key-pair --key-name "$resource_name" --key-type ed25519 \
        --query KeyMaterial --output text > "$evidence/key.pem"
    chmod 600 "$evidence/key.pem"
    record KEY_NAME "$resource_name"
    record_output SG_ID run awsc ec2 create-security-group --group-name "$resource_name" \
        --description 'Coga clean-install harness: SSH from one address' \
        --vpc-id "$vpc" --query GroupId --output text
    # SSH only; VNC travels through an SSH tunnel, so 5900 stays closed.
    run awsc ec2 authorize-security-group-ingress --group-id "$SG_ID" \
        --protocol tcp --port 22 --cidr "$ip/32" >/dev/null

    local tags="Tags=[{Key=Name,Value=$resource_name},{Key=coga-clean-install,Value=$1}]"
    record_output HOST_ID run awsc ec2 allocate-hosts --instance-type mac2.metal \
        --availability-zone "$az" --quantity 1 \
        --tag-specifications "ResourceType=dedicated-host,$tags" \
        --query 'HostIds[0]' --output text
    record HOST_ALLOCATED_AT "$(date -u +%FT%TZ)"
    record_output INSTANCE_ID run awsc ec2 run-instances --image-id "$ami" \
        --instance-type mac2.metal --placement "Tenancy=host,HostId=$HOST_ID" \
        --key-name "$resource_name" --security-group-ids "$SG_ID" \
        --subnet-id "$subnet" --associate-public-ip-address \
        --tag-specifications "ResourceType=instance,$tags" \
        --query 'Instances[0].InstanceId' --output text
    run awsc ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    record_output PUBLIC_IP awsc ec2 describe-instances --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

    ssh_args
    echo 'Waiting for SSH (an EC2 Mac often needs 10-20 minutes to boot)'
    local tries=0
    until mac true 2>/dev/null; do
        (( ++tries < ${COGA_MAC_SSH_TRIES:-90} )) || { echo 'SSH never came up' >&2; false; }
        sleep "${COGA_MAC_SSH_WAIT:-20}"
    done
    run mac mkdir -p /tmp/coga-clean-install
    run scp "${ssh_opts[@]}" "$script_dir/macos-walk.sh" "$script_dir/container.sh" \
        "$target:/tmp/coga-clean-install/"
    run mac bash /tmp/coga-clean-install/macos-walk.sh baseline | tee "$evidence/baseline.txt"
    run mac bash /tmp/coga-clean-install/macos-walk.sh reset
    echo "Provisioned. Next: $0 walk $1 pypi|main MAC_USER"
}

walk() {
    [[ $# -ge 3 && $# -le 4 && $2 =~ ^(pypi|main)$ ]] || usage
    load "$1"
    local artifact=$2 user=$3 operator=${4:-installer}
    [[ $user =~ ^[a-z][a-z0-9]*$ ]] || { echo "MAC_USER must be a short lowercase name" >&2; exit 2; }
    local out="$evidence/walks/$user"
    [[ ! -e $out ]] || { echo "Walk evidence exists: $out; choose a new MAC_USER" >&2; exit 2; }
    mkdir -p "$out"
    ssh_args
    local password
    password=$(openssl rand -hex 12)
    (umask 077 && printf '%s\n' "$password" > "$out/password.txt")

    local mode=pypi remote_wheel=
    if [[ $artifact == main ]]; then
        # Export the fetched commit, never the caller's working tree.
        run git -C "$repo_root" fetch origin main
        local sha tmp wheels
        sha=$(git -C "$repo_root" rev-parse FETCH_HEAD)
        printf 'origin/main=%s\n' "$sha" | tee "$out/source.txt"
        tmp=$(mktemp -d)
        mkdir "$tmp/source"
        git -C "$repo_root" archive "$sha" | tar -x -C "$tmp/source"
        run uv build --wheel --no-sources --out-dir "$out/wheels" "$tmp/source"
        rm -rf -- "$tmp"
        wheels=("$out"/wheels/*.whl)
        [[ ${#wheels[@]} -eq 1 && -f ${wheels[0]} ]]
        run checksum "${wheels[0]}"
        remote_wheel="/tmp/coga-clean-install/$(basename -- "${wheels[0]}")"
        run scp "${ssh_opts[@]}" "${wheels[0]}" "$target:$remote_wheel"
        mode=wheel
    fi
    local status=0
    # Passwords stay out of the terminal and host.txt command trace.
    mac bash /tmp/coga-clean-install/macos-walk.sh walk \
        "$mode" "$operator" "$user" "$password" ${remote_wheel:+"$remote_wheel"} || status=$?
    fetch_evidence "$user" "$out"
    printf 'artifact=%s\nmac_user=%s\nexit_code=%s\n' "$artifact" "$user" "$status" | tee "$out/result.txt"
    echo "Continue attended: $0 ssh $1 sudo -iu $user"
    return "$status"
}

fetch_evidence() {
    mkdir -p "$2/mac"
    mac sudo tar -C "/Users/$1/clean-install" -cf - evidence | tar -x -C "$2/mac" ||
        echo "Could not copy walk evidence for $1; inspect over ssh"
}

vnc() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    ssh_args
    local password
    password=$(openssl rand -hex 12)
    (umask 077 && printf '%s\n' "$password" > "$evidence/vnc-password.txt")
    # Do not trace the password argument.
    mac bash /tmp/coga-clean-install/macos-walk.sh vnc "$password"
    printf 'Tunnel:  ssh -i %q -N -L 5900:localhost:5900 %s\n' "$evidence/key.pem" "$target"
    printf 'Then open vnc://localhost:5900 as ec2-user; password in %s\n' "$evidence/vnc-password.txt"
}

status() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    [[ -z ${INSTANCE_ID:-} ]] || awsc ec2 describe-instances --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].[InstanceId,State.Name]' --output text
    [[ -z ${HOST_ID:-} ]] || awsc ec2 describe-hosts --host-ids "$HOST_ID" \
        --query 'Hosts[0].[HostId,State,AllocationTime]' --output text
}

teardown() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    if [[ -n ${INSTANCE_ID:-} && -z ${INSTANCE_TERMINATED:-} ]]; then
        run awsc ec2 terminate-instances --instance-ids "$INSTANCE_ID" >/dev/null
        run awsc ec2 wait instance-terminated --instance-ids "$INSTANCE_ID"
        record INSTANCE_TERMINATED "$(date -u +%FT%TZ)"
    fi
    if [[ -n ${SG_ID:-} && -z ${SG_DELETED:-} ]]; then
        run awsc ec2 delete-security-group --group-id "$SG_ID"
        record SG_DELETED "$(date -u +%FT%TZ)"
    fi
    if [[ -n ${KEY_NAME:-} && -z ${KEY_DELETED:-} ]]; then
        run awsc ec2 delete-key-pair --key-name "$KEY_NAME" >/dev/null
        record KEY_DELETED "$(date -u +%FT%TZ)"
    fi
    release_host
}

release() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    release_host
}

release_host() {
    [[ -n ${HOST_ID:-} && -z ${HOST_RELEASED:-} ]] || return 0
    local failed
    failed=$(run awsc ec2 release-hosts --host-ids "$HOST_ID" \
        --query 'Unsuccessful[].Error.Message' --output text)
    if [[ -n $failed && $failed != None ]]; then
        echo "Host $HOST_ID NOT released: $failed"
        echo "It was allocated at $HOST_ALLOCATED_AT; a mac2 host can be released"
        echo "24 hours after that, once it leaves the post-termination 'pending' scrub."
        echo "It keeps billing until then. Retry: $0 release <NAME>"
        return 1
    fi
    record HOST_RELEASED "$(date -u +%FT%TZ)"
}

case $command in
preflight | provision | walk | vnc | status | teardown | release) "$command" "$@" ;;
ssh)
    load "$1"
    shift
    ssh_args
    exec ssh -t "${ssh_opts[@]}" "$target" "$@"
    ;;
*) usage ;;
esac
