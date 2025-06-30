---
id: junos_gnmimd
title: "GNMI without Certificates on Juniper"
description: "Config guide to run JunOS GNMI in insecure mode without certs"
created: 2024-01-20
author: "Network Automation Team"
version: "1.0"
category: "network-knowledge-base"
keywords:
  - gnmi
  - juniper
  - grpc
  - insecure-mode
training_questions:
  - How do I configure JunOS GNMI without certificates?
  - What port does JunOS use for insecure GNMI?
related_products:
  - vMX 22.3R1.11
  - vQFX 19.4R1.10
topics:
  - Network Telemetry
  - Juniper Configuration
---


## How to setup a JunOS device for GNMI 

The configuration is fairly simple for a lab scenario where we will not use certificates and use the insecure mode.
Please refer to the Juniper Site for details on configuration using Certificates.

This was tested on the vMX 22.3R1.11 and vQFX 19.4R1.10
Note: Although configuration is accepted on the vQFX it was not possible to get GNMI working on this platform. This could be due to the fact that the insecure mode is not supported in earlier releases 

## How to setup a JunOS device for GNMI without certificates {#gnmi_no_certs .Section primary="true"}
```
set system services extension-service request-response grpc clear-text port 57400
set system services extension-service request-response grpc max-connections 4
```

You will also need this for the reponse to be sent back to the client.

```
set system services extension-service request-response grpc routing-instance mgmt_junos
```