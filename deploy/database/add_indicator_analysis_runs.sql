SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.IndicatorAnalysisRun', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.IndicatorAnalysisRun (
        run_id bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
        user_id nvarchar(100) NOT NULL,
        created_at datetime2 NOT NULL CONSTRAINT DF_IndicatorAnalysisRun_CreatedAt DEFAULT SYSUTCDATETIME(),
        year_start int NOT NULL,
        year_end int NOT NULL,
        cancer_keys_json nvarchar(max) NOT NULL,
        definition_version_id int NULL,
        definition_version_name nvarchar(100) NOT NULL,
        definition_snapshot_json nvarchar(max) NOT NULL,
        result_snapshot_json nvarchar(max) NOT NULL,
        CONSTRAINT CK_IndicatorAnalysisRun_YearRange CHECK (year_start <= year_end),
        CONSTRAINT CK_IndicatorAnalysisRun_CancerKeysJson CHECK (ISJSON(cancer_keys_json) = 1),
        CONSTRAINT CK_IndicatorAnalysisRun_DefinitionSnapshotJson CHECK (ISJSON(definition_snapshot_json) = 1),
        CONSTRAINT CK_IndicatorAnalysisRun_ResultSnapshotJson CHECK (ISJSON(result_snapshot_json) = 1)
    );

    CREATE INDEX IX_IndicatorAnalysisRun_UserCreatedAt
        ON dbo.IndicatorAnalysisRun (user_id, created_at DESC);
    CREATE INDEX IX_IndicatorAnalysisRun_DefinitionVersion
        ON dbo.IndicatorAnalysisRun (definition_version_id, created_at DESC);
END

COMMIT TRANSACTION;
