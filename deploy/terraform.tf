#
# TERRAFORM CONFIGURATION
#

## CONFIGURATION ##
variable "domain" { default = "learningu.org"    }
variable "sites"  { default = ["test1", "test2"] }

variable "aws_access_key"  { type = "string" }
variable "aws_secret_key"  { type = "string" }
variable "aws_region"      { type = "string" }
variable "route53_zone_id" { type = "string" }

variable "postgresql_host" { type = "string" }
variable "postgresql_port" { type = "string" }
variable "postgresql_admin_user" { type = "string" }
variable "postgresql_admin_pass" { type = "string" }


provider "aws" {
  access_key = "${var.aws_access_key}"
  secret_key = "${var.aws_secret_key}"
  region     = "${var.aws_region}"
}

provider "lxd" {
  # create containers locally on the machine running Terraform
}

provider "postgresql" {
  host     = "${var.postgresql_host}"
  port     = "${var.postgresql_port}"
  username = "${var.postgresql_admin_user}"
  password = "${var.postgresql_admin_pass}"
}


data "external" "site_config" {
  count   = "${length(var.sites)}"
  program = ["/bin/cat", "/lu/shares/${var.sites[count.index]}/terraform.json"]
}


## CONTAINERS ##
resource "lxd_container" "vm" {
  count     = "${length(var.sites)}"
  name      = "${var.sites[count.index]}"
  image     = "ubuntu:16.04"
  ephemeral = false
  profiles  = ["default"] # to pick up eth0

  config {
    limits.cpu    = "${data.external.site_config.*.result.vm.cpu[count.index]}"
    limits.memory = "${data.external.site_config.*.result.vm.memory[count.index]}"
  }

  device {
    name = "share"
    type = "disk"

    properties {
      source = "/lu/shares/${var.sites[count.index]}"
      path   = "/lu/share"
    }
  }

  depends_on = ["random_id.django_secret_key", "random_id.db_password", "null_resource.email"]

  provisioner "local-exec" {
    command = "lxc file push --mode=755 /lu/esp-website/deploy/chef/bootstrap.sh '${var.sites[count.index]}/tmp/bootstrap.sh'"
  }

  provisioner "local-exec" {
    command = "lxc exec '${var.sites[count.index]}' -- /tmp/bootstrap.sh '${data.external.site_config.*.result.git.branch[count.index]}'"
  }
}

resource "random_id" "django_secret_key" {
  count       = "${length(var.sites)}"
  byte_length = 32

  keepers {
    site = "${var.sites[count.index]}"
  }

  provisioner "local-exec" {
    command = "echo '${self.b64}' >/lu/shares/${var.sites[count.index]}/django-secret-key"
  }
}


## DATABASE ###
resource "postgresql_database" "db" {
  count = "${length(var.sites)}"
  name  = "${var.sites[count.index]}"
  owner = "${postgresql_role.db_user.*.name[count.index]}"

  provisioner "local-exec" {
    command = <<EOF
echo 'host = ${var.postgresql_host}
port = ${var.postgresql_port}
database = ${self.name}
user = ${postgresql_role.db_user.*.name[count.index]}
password = ${random_id.db_password.*.hex[count.index]}' >/lu/shares/${var.sites[count.index]}/database.ini
EOF
  }
}

resource "postgresql_role" "db_user" {
  count    = "${length(var.sites)}"
  name     = "${var.sites[count.index]}"
  login    = true
  password = "${random_id.db_password.*.hex[count.index]}"
}

resource "random_id" "db_password" {
  count       = "${length(var.sites)}"
  byte_length = 32

  keepers = {
    database = "${var.sites[count.index]}"
  }
}


## EMAIL ##
resource "aws_iam_user" "email" {
  name = "machine-email"
}

resource "aws_iam_access_key" "email" {
  user = "${aws_iam_user.email.name}"
}

resource "aws_iam_user_policy" "email" {
  name = "AmazonSesSendingAccess"
  user = "${aws_iam_user.email.name}"

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ses:SendRawEmail",
            "Resource": "*"
        }
    ]
}
EOF
}

resource "aws_ses_domain_identity" "email" {
  count  = "${length(var.sites)}"
  domain = "${var.sites[count.index]}.${var.domain}"
}

resource "aws_route53_record" "ses_verification" {
  count   = "${length(var.sites)}"
  zone_id = "${var.route53_zone_id}"
  name    = "_amazonses.${var.sites[count.index]}.${var.domain}"
  type    = "TXT"
  ttl     = "600"
  records = ["${aws_ses_domain_identity.email.*.verification_token[count.index]}"]
}

resource "null_resource" "email" {
  count = "${length(var.sites)}"

  triggers {
    key_id   = "${aws_iam_access_key.email.id}"
    password = "${aws_iam_access_key.email.ses_smtp_password}"
  }

  provisioner "local-exec" {
    command = <<EOF
echo 'host = email-smtp.${var.aws_region}.amazonaws.com
port = 465
user = ${aws_iam_access_key.email.id}
password = ${aws_iam_access_key.email.ses_smtp_password}' >/lu/shares/${var.sites[count.index]}/email.ini
EOF
  }
}
