# Azure DP-900 Data Platform & DSA System Architecture

**Document Version:** 2.0  
**Domain Alignment:** Microsoft Azure Data Fundamentals (DP-900) & Classical Data Structures & Algorithms (DSA)  
**Project:** LabVault  -  Academic Laboratory Resource Management Platform  

---

## 1. Executive Summary

LabVault is an enterprise-grade academic laboratory resource management platform built on Django 5.2. It organizes, validates, deduplicates, and serves academic resources including lab manuals, syllabi, experiment datasheets, and practical source code.

This architecture integrates **Azure DP-900 Cloud Data Fundamentals** across relational, non-relational, object storage, and analytics services, paired with deterministic **Data Structures and Algorithms (DSA)** for search, deduplication, and authorization.

---

## 2. Azure DP-900 Data Platform Alignment

```
                              +-------------------------------------------+
                              |         Client Presentation Layer         |
                              |   (Templates, Tokens CSS, GSAP Motion)    |
                              +---------------------+---------------------+
                                                    | HTTPS / TLS 1.3
                                                    v
                              +---------------------+---------------------+
                              |         Django Application Layer          |
                              |   Auth, RBAC, Rate-Limiting, Validation   |
                              +---------+-------------------+-------------+
                                        |                   |
            +---------------------------+                   +--------------------------+
            | TDS / Port 1433                               | HTTPS / SAS Token
            v                                               v
+-------------------------------+               +--------------------------------------+
|    Azure SQL Database         |               |      Azure Blob Storage              |
|    (Relational / OLTP)        |               |      (Object Store / Hot Tier)       |
|  - Users, Roles, Resources    |               |  - Lab Manuals, Code ZIPs, PDFs      |
|  - Normalized 3NF Schema      |               |  - AES-256 SSE Encryption at Rest    |
|  - B-Tree Clustered Indexes   |               |  - Private Container with SAS URLs   |
+---------------+---------------+               +------------------+-------------------+
                |                                                  |
                | Automated ETL / ELT                              |
                v                                                  v
+--------------------------------------------------------------------------------------+
|                           Azure Data Factory (ADF)                                   |
|               Scheduled Batch Extraction, Pipeline Orchestration                     |
+---------------------------------------+----------------------------------------------+
                                        |
                                        v
+--------------------------------------------------------------------------------------+
|                     Azure Synapse Analytics & Azure Data Lake Gen2                   |
|               Analytical Queries, Resource Usage Trends, Power BI Dashboards         |
+--------------------------------------------------------------------------------------+
```

### 2.1 Relational Data: Azure SQL Database
- **Role in Platform:** Primary transactional system of record (OLTP).
- **Engine:** Microsoft SQL Server / Azure SQL Database via `mssql-django` and `pyodbc`.
- **Normalization:** 3NF (Third Normal Form) across `Users`, `Resources`, `Categories`, `Subjects`, `ResourceSubjects`, `AccessLog`, and `Notifications`.
- **ACID Guarantee:** Strict atomicity and consistency during multipart file uploads and category reassignments.
- **Security:** Transparent Data Encryption (TDE) at rest, encrypted TDS connection (`Encrypt=yes;TrustServerCertificate=no`), and parameterized queries eliminating SQL injection.

### 2.2 Object Storage: Azure Blob Storage
- **Role in Platform:** Unstructured file repository for uploaded laboratory documents.
- **Tiers:** Hot tier for active semester manuals; automated lifecycle policies to Cool tier for prior academic years.
- **Security:** Storage Service Encryption (SSE) with 256-bit AES; private container access strictly delegated through short-lived (30 min) Shared Access Signature (SAS) tokens generated only after user authorization.
- **Development Fallback:** Zero-cloud local fallback using `LocalProtectedStorage` under `MEDIA_ROOT`.

### 2.3 Non-Relational / Semi-Structured: Azure Cosmos DB Integration Pattern
- **Role:** Telemetry, audit trail logging, and unstructured metadata for laboratory sensors or experiment outputs.
- **Data Model:** Core (SQL) API document store providing flexible schema JSON documents for high-volume audit logs without relational lock contention.

### 2.4 Modern Data Warehouse & Analytics: Azure Data Factory & Azure Synapse
- **Pipelines:** Azure Data Factory orchestrates scheduled daily differential extraction from Azure SQL `AccessLog` and `Resources` tables into Parquet files in Azure Data Lake Storage Gen2.
- **Reporting:** Synapse serverless SQL pools enable departmental reporting (e.g., most accessed lab manuals, storage consumption per semester, instructor submission frequencies) visualized via Power BI.

---

## 3. Data Structures and Algorithms (DSA) Implementation

LabVault avoids artificial complexity, utilizing algorithmic structures where they provide measurable performance and security benefits:

| Capability | Algorithm / Data Structure | Time Complexity | Space Complexity | Practical Engineering Rationale |
|---|---|---|---|---|
| **Resource Search** | B-Tree Clustered / Non-Clustered Indexes | $O(\log N)$ lookup | $O(N)$ auxiliary disk | Replaces $O(N)$ full table scans with logarithmic index seeks on `Title`, `CategoryId`, and `CreatedAt`. |
| **File Deduplication** | Cryptographic Stream Hash (SHA-256) | $O(M)$ stream read ($M$ = file bytes) | $O(1)$ constant buffer (64 KB) | Prevents storing redundant files on Azure Blob Storage by hashing incoming chunks before writing to disk. |
| **Duplicate Lookup** | Hash Table Index on Hex Digest | $O(1)$ average | $O(N)$ index storage | Immediate identification of identical uploaded files across subjects. |
| **Pagination & Sorting** | Two-pass SQL `OFFSET...FETCH` with B-Tree ordering | $O(\log N + K)$ ($K$ = page size) | $O(K)$ in-memory buffer | Stable memory footprint regardless of dataset size; avoids loading millions of records into memory. |
| **RBAC Authorization** | Set Membership / Bitwise Flag Check | $O(1)$ constant time | $O(1)$ space | Immediate evaluation of `_user_can_view_resource` and `_user_can_edit_resource`. |

### 3.1 SHA-256 Stream Deduplication Algorithm
```python
def compute_sha256(file_stream, chunk_size=65536):
    """
    Algorithmic Complexity:
      Time: O(M) where M is byte length of stream.
      Space: O(1) auxiliary memory using 64 KB rolling buffer.
    """
    sha256 = hashlib.sha256()
    file_stream.seek(0)
    for chunk in iter(lambda: file_stream.read(chunk_size), b""):
        sha256.update(chunk)
    file_stream.seek(0)
    return sha256.hexdigest()
```

---

## 4. Cybersecurity Controls Summary

1. **Authentication Security:**
   - Password hashing: Argon2id (`django.contrib.auth.hashers.Argon2PasswordHasher`) with PBKDF2 fallbacks.
   - Cryptographically signed single-use password reset tokens with 30-minute expiration (`PASSWORD_RESET_TIMEOUT = 1800`).
   - Generic authentication responses preventing email enumeration attacks.
2. **Session & Cookie Protection:**
   - `SESSION_COOKIE_HTTPONLY = True` preventing client-side script read.
   - `SESSION_COOKIE_SAMESITE = 'Lax'` mitigating Cross-Site Request Forgery (CSRF).
   - `CSRF_COOKIE_HTTPONLY = True`.
3. **File Upload Security:**
   - Magic-byte MIME signature verification (`detect_mime`) refusing renamed executable extensions.
   - 10 MB strict content-length cap (`DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760`).
   - Unpredictable random storage identifiers (`uuid4().hex + secrets.token_hex(8) + ext`) preventing path traversal and direct object enumeration.
4. **Header Hardening:**
   - `X_FRAME_OPTIONS = "DENY"` (clickjacking mitigation).
   - `SECURE_CONTENT_TYPE_NOSNIFF = True` (MIME sniffing mitigation).
   - `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"`.

