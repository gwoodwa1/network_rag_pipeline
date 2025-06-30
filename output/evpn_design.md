---
id: "evpn_leaf_spine_design"
title: "EVPN Leaf-Spine Network Design"
description: >
  Scalable BGP-EVPN-based data center fabric with VXLAN overlay and multi-tenant segmentation.
author: "Gary Woodward"
created: "2025-06-24"
version: "1.0"
category: "network-design"
type: "http://example.com/network-design#NetworkDesignDocument"
keywords:
  - EVPN
  - VXLAN
  - Leaf-Spine
  - BGP
  - DataCenter
  - Multitenancy
  - Underlay
  - Overlay
  - Automation
topics:
  - EVPN Architecture
  - BGP Control Plane
  - Data Center Fabric Design
  - VXLAN Overlay Networks
  - Network Security
  - Infrastructure as Code
relatedProducts:
  - "DataCorp Fabric v1.0"
trainingQuestions:
  - "What role does EVPN play in this architecture?"
  - "How are BGP ASNs structured for underlay and overlay?"
  - "What security features are applied at the tunnel level?"
  - "How does the VXLAN VNI allocation strategy support scalability?"
  - "What are the benefits of using L3VNIs in this fabric?"
  - "How is automation integrated with the design?"
complianceStandards:
  - PCI DSS
  - SOC 2 Type II
  - NIST CSF
status: "approved"
reviewed: "2025-06-26"
---

# EVPN Leaf-Spine Network Design Document

## Executive Summary

This document presents the network architecture design for DataCorp's new data center infrastructure utilizing Ethernet VPN (EVPN) technology in a leaf-spine topology. The design addresses the organization's requirements for scalable multi-tenancy, Layer 2 extension capabilities, and modern data center networking practices while maintaining operational simplicity and robust security posture.

## Introduction

Modern data center networks require architectures that can scale horizontally while providing consistent low-latency connectivity and supporting virtualized workloads. Traditional spanning tree-based designs have given way to more sophisticated approaches that leverage BGP-based control planes and VXLAN data planes to achieve these goals.

Our EVPN leaf-spine design represents a significant evolution from legacy three-tier architectures, providing several key advantages:

**Architectural Benefits:**
- **Horizontal Scalability**: The spine-leaf topology allows linear scaling by adding leaf switches without redesigning the core network
- **Predictable Performance**: Every leaf switch is exactly two hops away from any other leaf, ensuring consistent latency characteristics
- **Loop-Free Design**: BGP-based control plane eliminates the need for Spanning Tree Protocol in the underlay network
- **Multi-Tenancy Support**: EVPN provides native support for VRF-based tenant isolation with flexible policy enforcement

**Technical Innovation:**
The design leverages EVPN Type-2 and Type-5 routes to provide both Layer 2 and Layer 3 VPN services over a single unified infrastructure. VXLAN encapsulation enables overlay networks that are completely independent of the physical underlay topology, allowing for seamless virtual machine mobility and simplified network provisioning.

**Business Alignment:**
This architecture directly supports DataCorp's strategic initiatives around cloud-first infrastructure, DevOps automation, and multi-tenant service delivery. The programmable nature of EVPN networks enables infrastructure-as-code practices and rapid service deployment cycles that align with modern application development methodologies.

## Network Topology Overview

### Physical Architecture

The network implements a standard two-tier leaf-spine architecture optimized for east-west traffic patterns typical in modern data centers:

```
                    ┌─────────────┐    ┌─────────────┐
                    │   Spine-1   │    │   Spine-2   │
                    │ 10.0.0.11   │    │ 10.0.0.12   │
                    └─────────────┘    └─────────────┘
                           │                  │
                    ┌──────┼──────────────────┼──────┐
                    │      │                  │      │
              ┌─────────┐  │            ┌─────────┐  │
              │  Leaf1  │  │    ...     │  Leaf6  │  │
              │ AS65001 │  │            │ AS65003 │  │
              └─────────┘  │            └─────────┘  │
                           │                         │
                    ┌─────────────────────────────────┐
                    │        Host Networks           │
                    │    VLAN 10: 172.16.10.0/24    │
                    │    VLAN 20: 172.16.20.0/24    │
                    └─────────────────────────────────┘
```

### Addressing Scheme

The design utilizes a hierarchical addressing structure that separates underlay infrastructure from overlay tenant networks:

**Underlay Networks:**
- Loopback Addresses: `10.0.0.0/24` (BGP Router IDs)
- VTEP Addresses: `10.100.100.0/24` (VXLAN Tunnel Endpoints)
- Point-to-Point Links: `10.1.0.0/16` and `10.2.0.0/16` (Spine-1 and Spine-2 respectively)
- Management Network: `192.168.0.0/24`

**Overlay Networks:**
- VLAN 10: `172.16.10.0/24` (Production Environment)
- VLAN 20: `172.16.20.0/24` (Development Environment)

## Design Decisions

### BGP AS Number Strategy

The design implements a hub-and-spoke BGP topology using distinct Autonomous System numbers:

```bash
# Spine switches (Route Reflectors)
router bgp 65000

# Leaf switches (unique AS per leaf)
# Leaf6 configuration
router bgp 65003
```

**Rationale:** Using unique AS numbers per leaf switch enables:
- Simplified route filtering and policy application
- Clear administrative boundaries for troubleshooting
- Compliance with BGP best practices for EVPN deployments
- Future flexibility for complex multi-site scenarios

### VXLAN Network Identifier (VNI) Allocation

VNI assignment follows a structured approach that embeds VLAN information:

```bash
# VLAN-to-VNI mapping
vxlan vlan 10 vni 1000010  # Pattern: 10000 + VLAN ID
vxlan vlan 20 vni 1000020
vxlan vrf CLIENTS vni 1000000  # L3VNI for inter-VLAN routing
```

**Design Considerations:**
- Predictable VNI allocation simplifies network operations
- 24-bit VNI space provides ample room for future growth
- L3VNI separation enables efficient inter-VLAN routing
- Consistent numbering across all leaf switches

### Redundancy and High Availability

Physical redundancy is achieved through:

```bash
# Dual-homed spine connectivity
interface Port-Channel20
   description to_Spine-1
   ip address 10.1.6.1/30

interface Port-Channel10
   description to_Spine-2
   ip address 10.2.6.1/30
```

**Link Aggregation Benefits:**
- Increased bandwidth utilization (2x 10GbE = 20GbE effective)
- Sub-second failover through LACP
- Load distribution across physical links
- Simplified configuration management

### MTU Optimization

Jumbo frame configuration across the fabric:

```bash
# 9214-byte MTU on all fabric interfaces
interface Port-Channel20
   mtu 9214
interface Ethernet1
   mtu 9214
```

**Justification:**
- Accommodates VXLAN overhead (50 bytes) while maintaining 9000-byte payload
- Reduces packet fragmentation and improves throughput
- Industry standard for data center fabrics
- Future-proofs for additional encapsulation requirements

## Security Architecture

### Network Segmentation Strategy

The security architecture implements defense-in-depth principles through multiple isolation mechanisms:

**VRF-Based Tenant Isolation:**
```bash
vrf instance CLIENTS
   description Clients networks

# VRF-aware interfaces
interface Vlan10
   vrf CLIENTS
   ip address virtual 172.16.10.1/24
```

This provides complete routing table separation between tenant networks, ensuring that traffic cannot traverse between VRFs without explicit policy configuration.

**VXLAN Tunnel Security:**
```bash
interface Vxlan1
   vxlan learn-restrict any
```

The `learn-restrict any` configuration prevents dynamic MAC learning, requiring all endpoint information to be distributed through the BGP EVPN control plane. This eliminates flood-and-learn behavior that could be exploited for network reconnaissance.

### Access Control Framework

**Port Security Implementation:**
```bash
interface Ethernet3
   description to_host2
   switchport mode trunk
   spanning-tree portfast
```

Host-facing interfaces utilize trunk mode with explicit VLAN assignments, preventing VLAN hopping attacks while supporting virtualized environments.

**BGP Route Filtering:**
```bash
neighbor evpn maximum-routes 12000 warning-only
neighbor underlay maximum-routes 12000 warning-only
```

Route limiting protects against route table exhaustion attacks and provides early warning of misconfigurations that could impact network stability.

### Cryptographic Controls

**Management Plane Security:**
```bash
username admin privilege 15 role network-admin secret sha512 $6$aCD32ZXIHf.MwRbY$LQXzjVJGmGQUtNlOcX4hhu0eU6fy5/onI3uwuXKruHOTnuK3SssP82E6/naU6clcGufhIxpoomQl.KGndzfvb0
```

Administrative access utilizes SHA-512 hashed passwords with role-based access control, ensuring strong authentication mechanisms.

**Data Plane Considerations:**
While the current implementation utilizes unencrypted VXLAN tunnels for performance optimization, the architecture supports future implementation of:
- IPSec encryption for VXLAN tunnels
- MACsec for physical link encryption
- Integration with external key management systems

### Monitoring and Compliance

**Security Event Logging:**
The design incorporates comprehensive logging capabilities for security event correlation:
- BGP session state changes
- MAC learning events
- VXLAN tunnel establishment
- Administrative access attempts

**Compliance Framework:**
The architecture aligns with industry security frameworks:
- PCI DSS network segmentation requirements
- SOC 2 Type II access controls
- NIST Cybersecurity Framework implementation

## Operational Support Systems (OSS)

### Network Automation and Orchestration

**Infrastructure as Code Implementation:**
The standardized configuration structure enables full automation through tools like Ansible, Terraform, and custom Python scripts:

```python
# Example automation template structure
leaf_config = {
    'hostname': 'leaf6',
    'loopback0': '10.0.0.6/32',
    'vtep_ip': '10.100.100.6/32',
    'asn': '65003',
    'spine_connections': [
        {'spine': 'spine-1', 'ip': '10.1.6.1/30'},
        {'spine': 'spine-2', 'ip': '10.2.6.1/30'}
    ]
}
```

**Configuration Management:**
- Git-based version control for all network configurations
- Automated compliance checking against security baselines
- Rollback capabilities for rapid issue resolution
- Integration with CI/CD pipelines for network changes

### Monitoring and Observability

**Telemetry Collection Strategy:**
```bash
# Key metrics for collection
- BGP session status and route counts
- VXLAN tunnel state and traffic statistics  
- Interface utilization and error rates
- EVPN route advertisement/withdrawal events
```

**SNMP and Streaming Telemetry:**
The Arista EOS platform provides comprehensive telemetry capabilities:
- Real-time streaming telemetry for sub-second visibility
- Traditional SNMP for integration with existing NMS platforms
- gNMI support for modern network automation tools
- Custom EOS SDK applications for specialized monitoring

### Fault Management

**Proactive Monitoring:**
- BGP session monitoring with automatic alerting
- Interface utilization trending and capacity planning
- EVPN route table analysis for optimization opportunities
- Predictive analytics for hardware failure prevention

**Incident Response Framework:**
- Automated fault isolation through BGP route withdrawal
- Maintenance mode procedures for planned outages
- Documentation of common troubleshooting procedures
- Integration with enterprise ITSM platforms

### Performance Management

**Capacity Planning Metrics:**
- East-west traffic matrix analysis
- VTEP CPU and memory utilization tracking
- BGP control plane scaling metrics
- Tenant network growth projections

**Quality of Service (QoS):**
Future implementation will include:
- Application-aware traffic classification
- Dynamic bandwidth allocation per tenant
- Priority queuing for critical applications
- Network slice implementation for 5G services

## Configuration Examples

### Leaf Switch Base Configuration

```bash
# Hostname and basic services
hostname leaf6
service routing protocols model multi-agent
transceiver qsfp default-mode 4x10G

# VRF definition for tenant isolation
vrf instance CLIENTS
   description Clients networks

# VLAN definitions with descriptive names
vlan 10
   name Network_172.16.10.0
vlan 20
   name Network_172.16.20.0
```

### Underlay Network Configuration

```bash
# Spine-1 connectivity with port channeling
interface Port-Channel20
   description to_Spine-1
   no switchport
   mtu 9214
   ip address 10.1.6.1/30

interface Ethernet1
   description to_Spine-1-link1
   channel-group 20 mode active
   no switchport
   mtu 9214

# Spine-2 connectivity with redundant links
interface Port-Channel10
   description to_Spine-2
   no switchport
   mtu 9214
   ip address 10.2.6.1/30

interface Ethernet2
   description to_Spine-2-link1
   channel-group 10 mode active
   no switchport
   mtu 9214

interface Ethernet4
   description to_Spine-2-link2
   channel-group 10 mode active
   no switchport
   mtu 9214
```

### EVPN and VXLAN Configuration

```bash
# Loopback interfaces for BGP and VXLAN
interface Loopback0
   description BGP EVPN peering
   ip address 10.0.0.6/32

interface Loopback1
   description VXLAN VTEP
   ip address 10.100.100.6/32

# VXLAN tunnel interface
interface Vxlan1
   vxlan source-interface Loopback1
   vxlan virtual-router encapsulation mac-address local
   vxlan udp-port 4789
   vxlan vlan 10 vni 1000010
   vxlan vlan 20 vni 1000020
   vxlan vrf CLIENTS vni 1000000
   vxlan learn-restrict any

# Virtual gateway configuration
ip virtual-router mac-address c0:01:ca:fe:ba:be

# SVI configurations for tenant networks
interface Vlan10
   vrf CLIENTS
   ip address virtual 172.16.10.1/24

interface Vlan20
   vrf CLIENTS
   ip address virtual 172.16.20.1/24
```

### BGP EVPN Configuration

```bash
router bgp 65003
   router-id 10.0.0.6
   no bgp default ipv4-unicast
   distance bgp 20 200 200
   maximum-paths 4 ecmp 64

   # EVPN peer group for spine connections
   neighbor evpn peer-group
   neighbor evpn remote-as 65000
   neighbor evpn update-source Loopback0
   neighbor evpn ebgp-multihop 3
   neighbor evpn send-community extended
   neighbor evpn maximum-routes 12000 warning-only

   # Underlay peer group for IP fabric
   neighbor underlay peer-group
   neighbor underlay remote-as 65000
   neighbor underlay maximum-routes 12000 warning-only

   # Specific neighbor definitions
   neighbor 10.0.0.11 peer-group evpn
   neighbor 10.0.0.12 peer-group evpn
   neighbor 10.1.6.2 peer-group underlay
   neighbor 10.2.6.2 peer-group underlay

   # Address family configurations
   address-family evpn
      neighbor evpn activate

   address-family ipv4
      neighbor underlay activate
      network 10.0.0.6/32
      network 10.100.100.6/32

   # VRF-specific BGP configuration
   vrf CLIENTS
      rd 65003:1000000
      route-target import evpn 1:1000000
      route-target export evpn 1:1000000
      redistribute connected
```

## Testing and Validation

### Pre-Deployment Testing

**Lab Environment Validation:**
- Full topology simulation using containerized Arista vEOS
- Traffic generation and performance testing
- Failover scenario validation
- Configuration drift detection

### Deployment Validation Procedures

**Connectivity Testing:**
```bash
# Underlay reachability verification
ping 10.0.0.11 source 10.0.0.6
ping 10.0.0.12 source 10.0.0.6

# BGP session validation
show bgp evpn summary
show bgp ipv4 unicast summary

# VXLAN tunnel verification
show vxlan vtep
show vxlan vni
```

**Data Path Validation:**
- Inter-VLAN routing functionality
- MAC learning and aging behavior
- Multicast replication efficiency
- QoS marking preservation

## Conclusion

This EVPN leaf-spine network design provides DataCorp with a robust, scalable, and secure foundation for modern data center operations. The architecture successfully addresses the key requirements of multi-tenancy, high availability, and operational simplicity while positioning the organization for future growth and technology adoption.

The implementation of industry-standard protocols and best practices ensures long-term supportability and vendor independence, while the comprehensive security framework provides the necessary controls for regulatory compliance and risk management.

Future enhancements will focus on advanced automation capabilities, enhanced telemetry integration, and potential expansion to multi-site deployments using EVPN Type-5 routes for DCI connectivity.