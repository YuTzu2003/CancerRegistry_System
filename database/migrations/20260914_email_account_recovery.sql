/*
  Email binding and password recovery schema upgrade.
  Safe to run repeatedly on the hospital_data database.
*/

IF COL_LENGTH('dbo.Users', 'Email') IS NULL
    ALTER TABLE dbo.Users ADD Email NVARCHAR(254) NULL;
GO

IF COL_LENGTH('dbo.Users', 'EmailVerifiedAt') IS NULL
    ALTER TABLE dbo.Users ADD EmailVerifiedAt DATETIME2 NULL;
GO

IF COL_LENGTH('dbo.Users', 'EmailPromptDismissedAt') IS NULL
    ALTER TABLE dbo.Users ADD EmailPromptDismissedAt DATETIME2 NULL;
GO

/* Treat legacy empty values as no binding before creating the unique index. */
UPDATE dbo.Users SET Email = NULL WHERE LTRIM(RTRIM(ISNULL(Email, ''))) = '';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.Users') AND name = 'UX_Users_Email_NotNull'
)
    CREATE UNIQUE INDEX UX_Users_Email_NotNull
    ON dbo.Users (Email)
    WHERE Email IS NOT NULL;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.Users') AND name = 'UQ_Users_ID'
)
    CREATE UNIQUE INDEX UQ_Users_ID ON dbo.Users (ID);
GO
IF OBJECT_ID('dbo.AccountVerificationCodes', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.AccountVerificationCodes (
        VerificationCodeID UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT PK_AccountVerificationCodes PRIMARY KEY
            DEFAULT NEWID(),
        UserID UNIQUEIDENTIFIER NOT NULL,
        Email NVARCHAR(254) NOT NULL,
        Purpose NVARCHAR(32) NOT NULL,
        CodeSalt CHAR(32) NOT NULL,
        CodeHash CHAR(64) NOT NULL,
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_AccountVerificationCodes_CreatedAt DEFAULT GETDATE(),
        ExpiresAt DATETIME2 NOT NULL,
        ConsumedAt DATETIME2 NULL,
        InvalidatedAt DATETIME2 NULL,
        AttemptCount INT NOT NULL CONSTRAINT DF_AccountVerificationCodes_AttemptCount DEFAULT 0,
        CONSTRAINT FK_AccountVerificationCodes_Users
            FOREIGN KEY (UserID) REFERENCES dbo.Users(ID),
        CONSTRAINT CK_AccountVerificationCodes_Purpose
            CHECK (Purpose IN ('EMAIL_BIND', 'PASSWORD_RESET')),
        CONSTRAINT CK_AccountVerificationCodes_AttemptCount
            CHECK (AttemptCount >= 0)
    );
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.AccountVerificationCodes')
      AND name = 'IX_AccountVerificationCodes_Active'
)
    CREATE INDEX IX_AccountVerificationCodes_Active
    ON dbo.AccountVerificationCodes (UserID, Purpose, CreatedAt DESC)
    INCLUDE (Email, ExpiresAt, ConsumedAt, InvalidatedAt, AttemptCount);
GO