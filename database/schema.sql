-- LabVault database schema (Microsoft SQL Server / Azure SQL Database)
-- Target: Third Normal Form (3NF)
-- Run against the target database BEFORE starting the application.
-- Never drop/truncate an existing database automatically.

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'LabVault')
BEGIN
    CREATE DATABASE LabVault;
END
GO

USE LabVault;
GO

-- Users table: accounts and authentication
CREATE TABLE Users (
    UserId INT IDENTITY(1,1) PRIMARY KEY,
    FullName NVARCHAR(100) NOT NULL,
    Email NVARCHAR(254) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(500) NOT NULL,
    Role NVARCHAR(20) NOT NULL DEFAULT 'student' CHECK (Role IN ('student', 'administrator')),
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME()
);
GO

-- Categories: resource categories
CREATE TABLE Categories (
    CategoryId INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(500) NULL
);
GO

-- Subjects: academic subjects/courses
CREATE TABLE Subjects (
    SubjectId INT IDENTITY(1,1) PRIMARY KEY,
    SubjectCode NVARCHAR(20) NOT NULL UNIQUE,
    SubjectName NVARCHAR(100) NOT NULL
);
GO

-- Resources: file metadata (3NF: depends only on ResourceId)
CREATE TABLE Resources (
    ResourceId INT IDENTITY(1,1) PRIMARY KEY,
    Title NVARCHAR(200) NOT NULL,
    Description NVARCHAR(2000) NULL,
    CategoryId INT NULL,
    UploadedBy INT NOT NULL,
    StorageKey NVARCHAR(200) NOT NULL UNIQUE,
    OriginalFileName NVARCHAR(260) NOT NULL,
    ContentType NVARCHAR(100) NOT NULL,
    FileSizeBytes BIGINT NOT NULL CHECK (FileSizeBytes >= 0),
    Visibility NVARCHAR(20) NOT NULL DEFAULT 'private' CHECK (Visibility IN ('private', 'public')),
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    UpdatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_Resources_Category FOREIGN KEY (CategoryId) REFERENCES Categories(CategoryId) ON DELETE SET NULL,
    CONSTRAINT FK_Resources_Uploader FOREIGN KEY (UploadedBy) REFERENCES Users(UserId) ON DELETE CASCADE
);
GO

-- ResourceSubjects: many-to-many between Resources and Subjects
CREATE TABLE ResourceSubjects (
    ResourceId INT NOT NULL,
    SubjectId INT NOT NULL,
    PRIMARY KEY (ResourceId, SubjectId),
    CONSTRAINT FK_ResourceSubjects_Resource FOREIGN KEY (ResourceId) REFERENCES Resources(ResourceId) ON DELETE CASCADE,
    CONSTRAINT FK_ResourceSubjects_Subject FOREIGN KEY (SubjectId) REFERENCES Subjects(SubjectId) ON DELETE CASCADE
);
GO

-- AuditLogs: security-relevant and administrative actions
CREATE TABLE AuditLogs (
    AuditId INT IDENTITY(1,1) PRIMARY KEY,
    ActorUserId INT NULL,
    Action NVARCHAR(100) NOT NULL,
    EntityType NVARCHAR(50) NOT NULL,
    EntityId INT NOT NULL,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT FK_AuditLogs_Actor FOREIGN KEY (ActorUserId) REFERENCES Users(UserId) ON DELETE SET NULL
);
GO

PRINT 'Schema created successfully.';
