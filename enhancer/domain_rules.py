"""
Static data for DevOps prompt enhancement.

Contains keyword maps for domain detection, dimension injection rules,
cloud provider contexts, and mode-specific templates.
"""

# --- Domain Detection Keywords ---
# Used in Stage 1 to identify which DevOps domains a prompt concerns.
# Structure mirrors WEIGHTED_SKILL_MAP in memory/tracker.py.

DOMAIN_KEYWORDS = {
    "ci_cd": [
        "pipeline",
        "ci/cd",
        "cicd",
        "github actions",
        "workflow",
        "deploy",
        "deployment",
        "build",
        "release",
        "artifact",
        "continuous integration",
        "continuous delivery",
        "jenkins",
        "gitlab ci",
        "circleci",
    ],
    "docker": [
        "docker",
        "container",
        "dockerfile",
        "compose",
        "image",
        "registry",
        "kubernetes",
        "k8s",
        "helm",
        "pod",
        "orchestration",
    ],
    "terraform": [
        "terraform",
        "infrastructure as code",
        "iac",
        "hcl",
        "tfstate",
        "module",
        "provider",
        "state file",
        "plan",
        "apply",
        "tofu",
    ],
    "aws": [
        "aws",
        "ec2",
        "s3",
        "lambda",
        "ecs",
        "eks",
        "rds",
        "iam",
        "vpc",
        "cloudfront",
        "dynamodb",
        "sqs",
        "sns",
        "cloudwatch",
        "route53",
        "elasticache",
    ],
    "security": [
        "security",
        "iam",
        "rbac",
        "secret",
        "credential",
        "encryption",
        "tls",
        "ssl",
        "certificate",
        "vulnerability",
        "compliance",
        "audit",
        "zero trust",
    ],
    "observability": [
        "monitoring",
        "logging",
        "alerting",
        "metrics",
        "prometheus",
        "grafana",
        "datadog",
        "cloudwatch",
        "tracing",
        "observability",
        "sli",
        "slo",
        "sla",
    ],
    "networking": [
        "vpc",
        "subnet",
        "load balancer",
        "dns",
        "route53",
        "cdn",
        "firewall",
        "ingress",
        "egress",
        "nat gateway",
        "peering",
    ],
    "cost": [
        "cost",
        "budget",
        "pricing",
        "savings",
        "reserved instance",
        "spot instance",
        "optimization",
        "finops",
        "right-sizing",
    ],
}


# --- Dimension Injection Rules ---
# Used in Stage 2 to inject missing DevOps considerations.
# For each domain, defines dimensions that a well-formed prompt should address.
# check_keywords: if ANY of these appear in the prompt, the dimension is considered covered.
# injection: the text to add if the dimension is missing.

DIMENSION_INJECTIONS = {
    "ci_cd": {
        "security": {
            "check_keywords": [
                "security",
                "secret",
                "permissions",
                "oidc",
                "pin",
                "token",
                "credential",
            ],
            "injection": "Consider security implications: action pinning, least-privilege permissions, secret management, and OIDC authentication.",
        },
        "rollback": {
            "check_keywords": [
                "rollback",
                "revert",
                "canary",
                "blue-green",
                "undo",
                "rollforward",
            ],
            "injection": "Include a rollback strategy: how to revert a failed deployment safely.",
        },
        "caching": {
            "check_keywords": ["cache", "caching", "artifact"],
            "injection": "Address build performance: dependency caching, artifact reuse, and build time optimization.",
        },
        "testing": {
            "check_keywords": [
                "test",
                "coverage",
                "lint",
                "validate",
                "quality gate",
            ],
            "injection": "Include testing requirements: what tests to run, coverage thresholds, and quality gates.",
        },
    },
    "terraform": {
        "security": {
            "check_keywords": [
                "security",
                "iam",
                "least-privilege",
                "encryption",
                "policy",
            ],
            "injection": "Address security: IAM least-privilege policies, encryption at rest and in transit, and secret management.",
        },
        "cost": {
            "check_keywords": [
                "cost",
                "budget",
                "pricing",
                "savings",
                "reserved",
                "spot",
            ],
            "injection": "Consider cost implications: instance sizing, reserved vs. on-demand pricing, and resource lifecycle policies.",
        },
        "state_management": {
            "check_keywords": ["state", "backend", "locking", "remote"],
            "injection": "Address state management: remote backend configuration, state locking, and state file security.",
        },
        "rollback": {
            "check_keywords": ["rollback", "revert", "plan", "destroy"],
            "injection": "Include a rollback plan: how to safely revert infrastructure changes if something goes wrong.",
        },
        "scalability": {
            "check_keywords": [
                "scale",
                "auto-scaling",
                "capacity",
                "load",
                "elastic",
            ],
            "injection": "Consider scalability: auto-scaling policies, capacity planning, and load-based resource management.",
        },
    },
    "docker": {
        "security": {
            "check_keywords": [
                "security",
                "scan",
                "vulnerability",
                "non-root",
                "readonly",
                "trivy",
            ],
            "injection": "Address container security: base image selection, vulnerability scanning, non-root users, and read-only filesystems.",
        },
        "performance": {
            "check_keywords": [
                "multi-stage",
                "layer",
                "cache",
                "size",
                "slim",
                "alpine",
            ],
            "injection": "Consider image optimization: multi-stage builds, layer caching, minimal base images, and image size reduction.",
        },
        "networking": {
            "check_keywords": ["network", "port", "expose", "dns", "bridge"],
            "injection": "Address container networking: port mappings, network isolation, and service discovery.",
        },
    },
    "aws": {
        "security": {
            "check_keywords": [
                "security",
                "iam",
                "encryption",
                "least-privilege",
                "kms",
            ],
            "injection": "Address AWS security: IAM policies following least-privilege, encryption (KMS), VPC security groups, and CloudTrail logging.",
        },
        "cost": {
            "check_keywords": [
                "cost",
                "budget",
                "pricing",
                "reserved",
                "spot",
                "savings",
            ],
            "injection": "Consider AWS cost: right-sizing instances, Reserved Instances or Savings Plans, spot instances for fault-tolerant workloads, and cost allocation tags.",
        },
        "scalability": {
            "check_keywords": [
                "scale",
                "auto-scaling",
                "elastic",
                "capacity",
                "load balancer",
            ],
            "injection": "Address scalability: Auto Scaling groups, Elastic Load Balancing, and capacity planning for peak loads.",
        },
        "reliability": {
            "check_keywords": [
                "backup",
                "disaster",
                "recovery",
                "multi-az",
                "failover",
                "redundancy",
                "ha",
                "high availability",
            ],
            "injection": "Consider reliability: multi-AZ deployment, backup strategies, disaster recovery planning, and health checks.",
        },
    },
    "security": {
        "compliance": {
            "check_keywords": [
                "compliance",
                "audit",
                "regulation",
                "soc",
                "hipaa",
                "pci",
                "gdpr",
            ],
            "injection": "Consider compliance requirements: audit logging, regulatory standards (SOC2, HIPAA, PCI-DSS), and evidence collection.",
        },
        "incident_response": {
            "check_keywords": [
                "incident",
                "response",
                "alert",
                "runbook",
                "escalation",
            ],
            "injection": "Address incident response: alerting thresholds, runbook procedures, and escalation paths.",
        },
    },
    "observability": {
        "alerting": {
            "check_keywords": [
                "alert",
                "threshold",
                "pager",
                "notification",
                "on-call",
            ],
            "injection": "Include alerting strategy: meaningful thresholds, alert fatigue prevention, and on-call notification routing.",
        },
        "dashboards": {
            "check_keywords": ["dashboard", "visualization", "graph", "panel"],
            "injection": "Consider dashboard design: key metrics to visualize, SLI/SLO tracking, and audience-appropriate views.",
        },
    },
    "networking": {
        "security": {
            "check_keywords": [
                "security group",
                "nacl",
                "firewall",
                "waf",
                "tls",
            ],
            "injection": "Address network security: security groups, NACLs, WAF rules, and TLS termination.",
        },
        "high_availability": {
            "check_keywords": [
                "multi-az",
                "failover",
                "redundancy",
                "ha",
                "backup",
            ],
            "injection": "Consider high availability: multi-AZ deployment, failover routing, and redundant network paths.",
        },
    },
    "cost": {
        "monitoring": {
            "check_keywords": [
                "monitor",
                "alert",
                "budget alert",
                "threshold",
                "tracking",
            ],
            "injection": "Include cost monitoring: budget alerts, anomaly detection, and regular cost review cadence.",
        },
        "tagging": {
            "check_keywords": ["tag", "label", "allocation", "chargeback"],
            "injection": "Address cost allocation: tagging strategy for cost attribution, team chargebacks, and resource ownership.",
        },
    },
}


# --- Cloud Provider Context ---
# Used in Stage 3 to prepend provider-specific context.

CLOUD_PROVIDER_CONTEXT = {
    "aws": (
        "Cloud provider context: AWS. "
        "Assume AWS-native services (IAM, S3, EC2, ECS, Lambda, CloudWatch, etc.). "
        "Reference AWS Well-Architected Framework pillars where relevant."
    ),
    "gcp": (
        "Cloud provider context: Google Cloud Platform. "
        "Assume GCP-native services (Cloud IAM, GCS, GCE, GKE, Cloud Functions, Cloud Monitoring, etc.)."
    ),
    "azure": (
        "Cloud provider context: Microsoft Azure. "
        "Assume Azure-native services (Azure AD, Blob Storage, VMs, AKS, Azure Functions, Azure Monitor, etc.)."
    ),
}


# --- Mode-Specific Templates ---
# Used in Stage 5 to shape the enhanced prompt for each review mode.
# Aligns with mentor/modes/*.txt behavior.

MODE_TEMPLATES = {
    "mentor": {
        "preamble": (
            "You are helping a DevOps learner understand and implement the following. "
            "Guide them through the reasoning, not just the answer."
        ),
        "structure_hint": (
            "Structure your response as:\n"
            "1. Conceptual explanation (the WHY)\n"
            "2. Implementation approach (the HOW)\n"
            "3. Common pitfalls to avoid\n"
            "4. Next steps for learning"
        ),
        "chain_of_thought": "Think through this step by step, explaining your reasoning at each stage.",
    },
    "review": {
        "preamble": (
            "You are performing a senior-level DevOps review. "
            "Be direct, precise, and production-focused."
        ),
        "structure_hint": (
            "Structure your response as:\n"
            "1. Summary assessment\n"
            "2. Critical issues (must fix)\n"
            "3. Warnings (should fix)\n"
            "4. Recommendations (nice to have)\n"
            "5. Overall maturity rating"
        ),
        "chain_of_thought": "Systematically evaluate each aspect before providing your assessment.",
    },
    "debug": {
        "preamble": (
            "You are troubleshooting a DevOps issue. "
            "Form hypotheses before jumping to solutions."
        ),
        "structure_hint": (
            "Structure your response as:\n"
            "1. Clarifying questions (what information is needed)\n"
            "2. Most likely hypotheses (ranked by probability)\n"
            "3. Diagnostic steps for each hypothesis\n"
            "4. Resolution approach once root cause is identified"
        ),
        "chain_of_thought": "Before proposing solutions, list your hypotheses and the evidence for/against each.",
    },
    "interview": {
        "preamble": (
            "You are conducting a senior DevOps engineer interview. "
            "Challenge design decisions and probe for depth."
        ),
        "structure_hint": (
            "Structure your response as:\n"
            "1. Initial design question\n"
            "2. Follow-up probes on trade-offs\n"
            "3. Edge cases to explore\n"
            "4. Expected depth of answer at each level (junior/mid/senior)"
        ),
        "chain_of_thought": "Consider what a senior interviewer would ask to differentiate between surface knowledge and deep understanding.",
    },
}
