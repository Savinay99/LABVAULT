-- LabVault optional non-sensitive sample data (seed).
-- Safe for development only. Never seed production with real credentials.
USE LabVault;
GO

-- Categories
INSERT INTO Categories (Name, Description) VALUES
('Laboratory Manuals', 'Official lab manuals for courses.'),
('Experiment Documents', 'Experiment procedures and observation records.'),
('Practical Notes', 'Student practical and lab session notes.'),
('Source Code', 'Programming assignments and lab source code.'),
('Project Documents', 'Capstone and minor project reports.'),
('Reference Materials', 'Academic references and reading material.');
GO

-- Subjects
INSERT INTO Subjects (SubjectCode, SubjectName) VALUES
('CS101', 'Introduction to Programming'),
('CS201', 'Data Structures and Algorithms'),
('EE101', 'Basic Electrical Engineering'),
('PH101', 'Engineering Physics'),
('MA101', 'Engineering Mathematics');
GO

PRINT 'Seed data inserted.';
