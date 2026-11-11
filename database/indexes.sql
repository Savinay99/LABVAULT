-- LabVault indexes
-- Based on observed query patterns: search, filters, pagination, ownership, audit.
USE LabVault;
GO

-- Resources: search + sort + pagination
CREATE INDEX IX_Resources_CreatedAt ON Resources(CreatedAt DESC);
CREATE INDEX IX_Resources_UploadedBy ON Resources(UploadedBy);
CREATE INDEX IX_Resources_Category ON Resources(CategoryId);
CREATE INDEX IX_Resources_Visibility ON Resources(Visibility);
CREATE INDEX IX_Resources_Title ON Resources(Title);
-- Full-text-ish search support via LIKE on Title/Description benefits from these.
CREATE INDEX IX_Resources_UploadedBy_CreatedAt ON Resources(UploadedBy, CreatedAt DESC);

-- ResourceSubjects: subject filter + resource lookup
CREATE INDEX IX_ResourceSubjects_SubjectId ON ResourceSubjects(SubjectId);
CREATE INDEX IX_ResourceSubjects_ResourceId ON ResourceSubjects(ResourceId);

-- Users: email lookup (auth) is covered by UNIQUE; role filter for dashboard.
CREATE INDEX IX_Users_Email ON Users(Email);
CREATE INDEX IX_Users_Role ON Users(Role);

-- AuditLogs: recent activity queries ordered by CreatedAt DESC.
CREATE INDEX IX_AuditLogs_CreatedAt ON AuditLogs(CreatedAt DESC);
CREATE INDEX IX_AuditLogs_Actor ON AuditLogs(ActorUserId);

PRINT 'Indexes created successfully.';
