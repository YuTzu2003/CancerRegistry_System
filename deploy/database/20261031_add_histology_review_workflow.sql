/*
  組織型態版本審核流程。
  執行後：既有版本視為「已核准」；新送出的組織型態版本會是「待審核」，
  只有管理員核准後才會套用至 dbo.Histology_code_mapping。
*/
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF COL_LENGTH('dbo.BranchCommits', 'ReviewStatus') IS NULL
BEGIN
    ALTER TABLE dbo.BranchCommits
        ADD ReviewStatus nvarchar(20) NOT NULL
            CONSTRAINT DF_BranchCommits_ReviewStatus DEFAULT (N'Approved');
END;

IF COL_LENGTH('dbo.BranchCommits', 'ReviewedByUserID') IS NULL
    ALTER TABLE dbo.BranchCommits ADD ReviewedByUserID nvarchar(50) NULL;

IF COL_LENGTH('dbo.BranchCommits', 'ReviewedByName') IS NULL
    ALTER TABLE dbo.BranchCommits ADD ReviewedByName nvarchar(100) NULL;

IF COL_LENGTH('dbo.BranchCommits', 'ReviewedAt') IS NULL
    ALTER TABLE dbo.BranchCommits ADD ReviewedAt datetime2(0) NULL;

COMMIT TRANSACTION;
GO

SET XACT_ABORT ON;
BEGIN TRANSACTION;

UPDATE dbo.BranchCommits
SET ReviewStatus = N'Approved'
WHERE ReviewStatus IS NULL OR LTRIM(RTRIM(ReviewStatus)) = N'';

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = N'CK_BranchCommits_ReviewStatus')
BEGIN
    ALTER TABLE dbo.BranchCommits WITH CHECK
        ADD CONSTRAINT CK_BranchCommits_ReviewStatus
        CHECK (ReviewStatus IN (N'Pending', N'Approved', N'Rejected'));
END;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_BranchCommits_DataTypeReviewStatusCreatedAt')
BEGIN
    CREATE INDEX IX_BranchCommits_DataTypeReviewStatusCreatedAt
        ON dbo.BranchCommits (DataType, ReviewStatus, CreatedAt DESC);
END;

COMMIT TRANSACTION;
