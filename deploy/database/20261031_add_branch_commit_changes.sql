/*
  將版本異動明細與版本主檔一起保存於 SQL Server。
  新送出的組織型態版本不再依賴伺服器上的 JSON 版本檔才能預覽或恢復。
*/
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.BranchCommitChanges', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.BranchCommitChanges (
        CommitId uniqueidentifier NOT NULL,
        ChangeOrder int NOT NULL,
        RecordId nvarchar(100) NOT NULL,
        Action nvarchar(10) NOT NULL,
        BeforeJson nvarchar(max) NOT NULL,
        AfterJson nvarchar(max) NOT NULL,
        CONSTRAINT PK_BranchCommitChanges PRIMARY KEY CLUSTERED (CommitId, ChangeOrder),
        CONSTRAINT FK_BranchCommitChanges_BranchCommits
            FOREIGN KEY (CommitId) REFERENCES dbo.BranchCommits (CommitId),
        CONSTRAINT CK_BranchCommitChanges_Action
            CHECK (Action IN (N'Create', N'Update', N'Delete'))
    );
END;

COMMIT TRANSACTION;
