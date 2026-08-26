IF COL_LENGTH('dbo.User_applications', 'RejectionReason') IS NULL
    ALTER TABLE dbo.User_applications ADD RejectionReason NVARCHAR(500) NULL;
