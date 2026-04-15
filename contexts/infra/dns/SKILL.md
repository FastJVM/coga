---
name: infra/dns
description: Use this when a customer is setting up their DNS records
---

# DNS - domain context

When a customer is setting up their DNS records, they have to set up SPF before setting up DKIM. 

They have to set up DKIM before setting their DMARC record to "reject"

## SPF setup

- Must be configured before anything else 

## DKIM Setup 

- Requires SPF to be in place

## DMARC

-Only set to "reject" after SPF and DKIM are confirmed working 