data "aws_route53_zone" "root-zone" {
  name = var.root-zone
}

resource "aws_route53_zone" "new-zone" {
  # checkov:skip=CKV2_AWS_39:  Requires wider discussion around log/event ingestion before implementing. To be picked up on conclusion of DBTP-974
  # checkov:skip=CKV2_AWS_38:  Requires wider discussion around implementation of DNSSEC - DBTP-1220
  for_each = toset(var.zones)
  name     = "${each.key}.${data.aws_route53_zone.root-zone.name}"
  tags     = local.tags
}

resource "aws_route53_record" "ns-records" {
  for_each = toset(var.zones)
  name     = "${each.key}.${data.aws_route53_zone.root-zone.name}"
  ttl      = 172800
  type     = "NS"
  zone_id  = data.aws_route53_zone.root-zone.zone_id
  records  = [for ns in aws_route53_zone.new-zone[each.key].name_servers : "${ns}."]
}
