#!/usr/bin/env bash
# Host-side driver for the Windows clean-install harness on an EC2 Windows
# Server instance. See the coga/testing/clean-install/windows-aws topic.
set -Eeuo pipefail
umask 077

usage() {
    cat >&2 <<'EOF'
usage (export AWS_PROFILE first; every aws call passes it):
  aws-windows.sh preflight REGION
  aws-windows.sh provision NAME REGION [AZ]   (COGA_CLEAN_INSTALL_ALLOCATE=yes)
  aws-windows.sh walk NAME pypi|main WIN_USER [OPERATOR]
  aws-windows.sh ssh NAME [REMOTE-COMMAND ...]
  aws-windows.sh checkout NAME REF
  aws-windows.sh rdp NAME
  aws-windows.sh status NAME
  aws-windows.sh teardown NAME
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
ami_pattern='Windows_Server-2025-English-Full-Base-*'
instance_type=${COGA_WIN_INSTANCE_TYPE:-t3.large}
remote_dir='C:\coga-clean-install'
walk_ps1="$remote_dir\\windows-walk.ps1"

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
        # ssh keeps its terminal and its stdout (callers capture it); everything else is logged.
        [[ $command == ssh ]] && return
        exec > >(tee -a "$evidence/host.txt") 2>&1
        printf '\n=== %s %s %s\n' "$(date -u +%FT%TZ)" "$command" "$name"
    fi
}

ssh_args() {
    # Keepalives end a session whose route died (a VPN switching exits)
    # instead of leaving the host waiting forever.
    ssh_base=(-o StrictHostKeyChecking=accept-new
        -o UserKnownHostsFile="$evidence/known_hosts" -o ConnectTimeout=15
        -o ServerAliveInterval=30 -o ServerAliveCountMax=4)
    ssh_opts=(-i "$evidence/key.pem" -o IdentitiesOnly=yes "${ssh_base[@]}")
    target="Administrator@$PUBLIC_IP"
}

win_line() {
    # cmd.exe parses SSH commands before the executable sees them. Encode the
    # payload so metacharacters and %variables% never reach that parser. Start
    # the child directly: PowerShell 5.1's native invocation also loses empty
    # arguments and embedded quotes, so use ProcessStartInfo with CRT quoting.
    local words= word payload encoded
    for word in "$@"; do
        word=${word//\'/\'\'}
        words+="${words:+,}'$word'"
    done
    payload="\$words = @($words)"$'\n'
    payload+=$(cat <<'PS'
$ErrorActionPreference = 'Stop'
try {
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.FileName = $words[0]
    $quoted = @($words | Select-Object -Skip 1 | ForEach-Object {
        '"' + [regex]::Replace([regex]::Replace($_, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
    })
    $start.Arguments = $quoted -join ' '
    $start.UseShellExecute = $false
    $start.WorkingDirectory = (Get-Location).ProviderPath
    $child = [System.Diagnostics.Process]::Start($start)
    $child.WaitForExit()
    exit $child.ExitCode
} catch {
    [Console]::Error.WriteLine($_)
    exit 1
}
PS
)
    encoded=$(printf '%s' "$payload" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n') || return
    printf 'powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand %s' "$encoded"
}

win() {
    # The wrapper explicitly exits with the child's code, including non-1 codes.
    local line
    line=$(win_line "$@") || return
    ssh "${ssh_opts[@]}" "$target" "$line"
}

walk_ps() {
    win powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$walk_ps1" "$@"
}

as_user() {
    # ssh or scp with a walk user's password logon: the askpass helper reads
    # its password file. Options go before the destination and command.
    local program=$1
    shift
    SSH_ASKPASS="$askpass" SSH_ASKPASS_REQUIRE=force "$program" \
        -o PubkeyAuthentication=no -o PreferredAuthentications=password,keyboard-interactive \
        -o NumberOfPasswordPrompts=1 "${ssh_base[@]}" "$@"
}

latest_ami() {
    awsc ec2 describe-images --owners amazon \
        --filters "Name=name,Values=$ami_pattern" Name=architecture,Values=x86_64 \
        --query 'sort_by(Images,&CreationDate)[-1].[ImageId,Name]' --output text
}

repo_url() {
    # The box has no GitHub credentials; clone the public repo over HTTPS.
    if [[ -n ${COGA_WIN_REPO_URL:-} ]]; then
        printf '%s\n' "$COGA_WIN_REPO_URL"
        return
    fi
    local origin
    origin=$(git -C "$repo_root" remote get-url origin)
    origin=${origin%/}
    if [[ $origin =~ github\.com[:/]([^/]+)/([^/]+)$ ]]; then
        printf 'https://github.com/%s/%s.git\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]%.git}"
    else
        echo "Cannot derive a public HTTPS URL from $origin; set COGA_WIN_REPO_URL" >&2
        return 2
    fi
}

preflight() {
    [[ $# -eq 1 ]] || usage
    region=$1
    run awsc sts get-caller-identity --query Arn --output text
    echo 'Running On-Demand Standard instances vCPU quota:'
    awsc service-quotas get-service-quota --service-code ec2 --quota-code L-1216C47A \
        --query 'Quota.Value' --output text
    echo "Availability zones offering $instance_type:"
    awsc ec2 describe-instance-type-offerings --location-type availability-zone \
        --filters "Name=instance-type,Values=$instance_type" \
        --query 'InstanceTypeOfferings[].Location' --output text
    echo 'Harness instances not yet terminated:'
    awsc ec2 describe-instances --filters Name=tag-key,Values=coga-clean-install \
        Name=instance-state-name,Values=pending,running,stopping,stopped,shutting-down \
        --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags[?Key==`Name`]|[0].Value]' \
        --output text
    echo 'Newest Windows Server 2025 AMI:'
    latest_ami
}

user_data() {
    # EC2Launch runs this once at first boot as SYSTEM. Windows Server 2025
    # ships OpenSSH Server as a capability; install it if absent, trust the
    # harness key for administrators, start sshd and open 22 in the Windows
    # firewall. RDP stays reachable only through an SSH tunnel.
    cat <<EOF
<powershell>
\$ErrorActionPreference = 'Stop'
Start-Transcript -Path C:\\ProgramData\\coga-clean-install-userdata.log
if (-not (Get-Service sshd -ErrorAction SilentlyContinue)) {
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
}
\$keys = Join-Path \$env:ProgramData 'ssh\\administrators_authorized_keys'
New-Item -ItemType Directory -Force (Split-Path \$keys) | Out-Null
Set-Content -Path \$keys -Value '$1' -Encoding ascii
icacls.exe \$keys /inheritance:r /grant '*S-1-5-32-544:F' /grant '*S-1-5-18:F' | Out-Null
Set-Service sshd -StartupType Automatic
Start-Service sshd
# The image may already carry this rule, disabled or limited to some profiles.
if (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue) {
    Set-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -Enabled True -Profile Any -Action Allow
} else {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' \`
        -Enabled True -Profile Any -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}
Stop-Transcript
</powershell>
EOF
}

provision() {
    [[ $# -ge 2 && $# -le 3 ]] || usage
    load "$1"
    region=$2
    local az=${3:-}
    if [[ ${COGA_CLEAN_INSTALL_ALLOCATE:-} != yes ]]; then
        cat >&2 <<'EOF'
Refusing to provision: an EC2 Windows instance bills per second until teardown.
Follow the approval rule in the coga/testing/clean-install/windows-aws topic,
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
    record_output CALLER awsc sts get-caller-identity --query Arn --output text

    local ami ami_name subnet vpc ssh_from
    if [[ -n ${COGA_WIN_AMI:-} ]]; then
        ami=$COGA_WIN_AMI
        ami_name=$(awsc ec2 describe-images --image-ids "$ami" --query 'Images[0].Name' --output text)
    else
        read -r ami ami_name < <(latest_ami)
    fi
    [[ $ami == ami-* ]] || { echo "No Windows Server 2025 AMI found in $region" >&2; false; }
    record AMI "$ami"
    record AMI_NAME "$ami_name"
    if [[ -z $az ]]; then
        # Default subnets in zones that offer the instance type; take the first.
        local zones
        zones=$(awsc ec2 describe-instance-type-offerings --location-type availability-zone \
            --filters "Name=instance-type,Values=$instance_type" \
            --query 'InstanceTypeOfferings[].Location' --output text | tr '\t' ',')
        [[ -n $zones ]] || { echo "No zone in $region offers $instance_type" >&2; false; }
        az=$(awsc ec2 describe-subnets \
            --filters "Name=availability-zone,Values=$zones" Name=default-for-az,Values=true \
            --query 'sort_by(Subnets,&AvailabilityZone)[0].AvailabilityZone' --output text)
    fi
    record AZ "$az"
    record INSTANCE_TYPE "$instance_type"
    read -r subnet vpc < <(awsc ec2 describe-subnets \
        --filters "Name=availability-zone,Values=$az" Name=default-for-az,Values=true \
        --query 'Subnets[0].[SubnetId,VpcId]' --output text)
    [[ $subnet == subnet-* ]] || { echo "No default subnet in $az" >&2; false; }
    # A VPN may leave from several addresses in one range; then set
    # COGA_WIN_SSH_FROM to that range instead of the single checked address.
    ssh_from=${COGA_WIN_SSH_FROM:-$(curl -fsS https://checkip.amazonaws.com)/32}
    [[ $ssh_from =~ ^[0-9]+(\.[0-9]+){3}/[0-9]+$ ]] || { echo "Bad SSH source CIDR: $ssh_from" >&2; false; }
    record SSH_FROM "$ssh_from"

    # RSA, not ed25519: get-password-data decrypts the Administrator password
    # only with an RSA key pair, and rdp needs that password.
    run awsc ec2 create-key-pair --key-name "$resource_name" --key-type rsa --key-format pem \
        --query KeyMaterial --output text > "$evidence/key.pem"
    chmod 600 "$evidence/key.pem"
    record KEY_NAME "$resource_name"
    record_output SG_ID run awsc ec2 create-security-group --group-name "$resource_name" \
        --description 'Coga clean-install harness: SSH from one address' \
        --vpc-id "$vpc" --query GroupId --output text
    # SSH only; RDP travels through an SSH tunnel, so 3389 stays closed.
    run awsc ec2 authorize-security-group-ingress --group-id "$SG_ID" \
        --protocol tcp --port 22 --cidr "$ssh_from" >/dev/null

    user_data "$(ssh-keygen -y -f "$evidence/key.pem") $resource_name" > "$evidence/user-data.ps1"
    local tags="Tags=[{Key=Name,Value=$resource_name},{Key=coga-clean-install,Value=$1}]"
    record_output INSTANCE_ID run awsc ec2 run-instances --image-id "$ami" \
        --instance-type "$instance_type" \
        --key-name "$resource_name" --security-group-ids "$SG_ID" \
        --subnet-id "$subnet" --associate-public-ip-address \
        --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=${COGA_WIN_DISK_GB:-50},VolumeType=gp3,DeleteOnTermination=true}" \
        --metadata-options HttpTokens=required \
        --user-data "file://$evidence/user-data.ps1" \
        --tag-specifications "ResourceType=instance,$tags" "ResourceType=volume,$tags" \
        --query 'Instances[0].InstanceId' --output text
    record LAUNCHED_AT "$(date -u +%FT%TZ)"
    run awsc ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    record_output PUBLIC_IP awsc ec2 describe-instances --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text

    ssh_args
    echo 'Waiting for SSH (first boot and the OpenSSH install take about 5-15 minutes)'
    local tries=0
    until win cmd.exe /c 'exit 0' 2>/dev/null; do
        (( ++tries < ${COGA_WIN_SSH_TRIES:-80} )) || { echo 'SSH never came up' >&2; false; }
        sleep "${COGA_WIN_SSH_WAIT:-15}"
    done
    run win cmd.exe /c "mkdir $remote_dir"
    run scp "${ssh_opts[@]}" "$script_dir/windows-walk.ps1" "$target:C:/coga-clean-install/"
    {
        echo '## As launched'
        run walk_ps baseline
        run walk_ps setup >&2
        printf '\n## After setup (Git for Windows; uv and Python 3.11 for Administrator)\n'
        run walk_ps baseline
    } | tee "$evidence/baseline.txt"
    echo "Provisioned. Next: $0 walk $1 pypi|main WIN_USER   or   $0 checkout $1 main"
}

walk() {
    [[ $# -ge 3 && $# -le 4 && $2 =~ ^(pypi|main)$ ]] || usage
    load "$1"
    local artifact=$2 user=$3 operator=${4:-installer}
    [[ $user =~ ^[a-z][a-z0-9]{0,19}$ ]] || { echo "WIN_USER must be a short lowercase name" >&2; exit 2; }
    local out="$evidence/walks/$user"
    [[ ! -e $out ]] || { echo "Walk evidence exists: $out; choose a new WIN_USER" >&2; exit 2; }
    mkdir -p "$out"
    ssh_args
    local password
    # Windows' default policy wants three character classes.
    password="Cg-$(openssl rand -hex 12)"
    (umask 077 && printf '%s\n' "$password" > "$out/password.txt")
    askpass="$out/askpass.sh"
    printf '#!/bin/sh\ncat %q\n' "$out/password.txt" > "$askpass"
    chmod 700 "$askpass"

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
        remote_wheel="$remote_dir\\$(basename -- "${wheels[0]}")"
        run scp "${ssh_opts[@]}" "${wheels[0]}" "$target:C:/coga-clean-install/"
        mode=wheel
    fi
    # The password goes on stdin, never into a command line or host.txt.
    printf '%s\n' "$password" | run walk_ps adduser "$user"
    local status=0 line
    line=$(win_line powershell.exe -NoProfile \
        -ExecutionPolicy Bypass -File "$walk_ps1" walk "$mode" "$operator" ${remote_wheel:+"$remote_wheel"})
    as_user ssh "$user@$PUBLIC_IP" "$line" ||
        status=$?
    mkdir -p "$out/windows"
    as_user scp -r "$user@$PUBLIC_IP:clean-install/evidence" "$out/windows/" ||
        echo "Could not copy walk evidence for $user; inspect over ssh"
    printf 'artifact=%s\nwin_user=%s\nexit_code=%s\n' "$artifact" "$user" "$status" | tee "$out/result.txt"
    printf 'Continue as %s: ssh -o UserKnownHostsFile=%q %s@%s  (password in %s)\n' \
        "$user" "$evidence/known_hosts" "$user" "$PUBLIC_IP" "$out/password.txt"
    return "$status"
}

checkout() {
    [[ $# -eq 2 ]] || usage
    load "$1"
    ssh_args
    local url
    url=$(repo_url)
    run walk_ps checkout "$2" "$url"
    echo "Fix loop: $0 ssh $1 uv run --directory coga-work python -m pytest"
}

rdp() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    ssh_args
    local password port=${COGA_WIN_RDP_PORT:-13389}
    # EC2Launch publishes the encrypted password a few minutes after boot.
    password=$(awsc ec2 get-password-data --instance-id "$INSTANCE_ID" \
        --priv-launch-key "$evidence/key.pem" --query PasswordData --output text)
    if [[ -z $password || $password == None ]]; then
        echo 'No Administrator password yet; EC2Launch publishes it a few minutes after first boot. Retry.'
        return 1
    fi
    (umask 077 && printf '%s\n' "$password" > "$evidence/admin-password.txt")
    printf 'Tunnel:  ssh -i %q -o IdentitiesOnly=yes -o UserKnownHostsFile=%q -N -L %s:localhost:3389 %s\n' \
        "$evidence/key.pem" "$evidence/known_hosts" "$port" "$target"
    printf 'Then connect an RDP client to localhost:%s as Administrator (e.g. xfreerdp /v:localhost:%s /u:Administrator);\n' "$port" "$port"
    printf 'password in %s. A walk user logs in with its walks/<user>/password.txt.\n' "$evidence/admin-password.txt"
}

status() {
    [[ $# -eq 1 ]] || usage
    load "$1"
    [[ -z ${INSTANCE_ID:-} ]] || awsc ec2 describe-instances --instance-ids "$INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].[InstanceId,State.Name,LaunchTime]' --output text
    echo 'Volumes tagged for this run (none once terminated):'
    awsc ec2 describe-volumes --filters "Name=tag:coga-clean-install,Values=$1" \
        --query 'Volumes[].[VolumeId,State,Size]' --output text
    [[ -z ${SG_ID:-} || -n ${SG_DELETED:-} ]] || echo "Security group $SG_ID not deleted"
    [[ -z ${KEY_NAME:-} || -n ${KEY_DELETED:-} ]] || echo "Key pair $KEY_NAME not deleted"
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
}

case $command in
preflight | provision | walk | checkout | rdp | status | teardown) "$command" "$@" ;;
ssh)
    load "$1"
    shift
    ssh_args
    if [[ $# -eq 0 ]]; then
        exec ssh -t "${ssh_opts[@]}" "$target"
    fi
    # Each word stays one argv word on Windows; see win_line.
    win "$@"
    ;;
*) usage ;;
esac
