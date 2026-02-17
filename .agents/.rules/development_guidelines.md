# プロキシ利用料管理システム 開発ガイドライン

本ドキュメントは、コードの品質・保守性・監査対応力を担保するための開発規約を定義する。
すべての開発者およびAIエージェントは、本ガイドラインに従って実装を行うこと。

---

## 1. 関数型プログラミング（Functional Programming）

### 1.1 基本方針

実装は関数型プログラミングのパラダイムに基づいて行う。副作用を最小化し、テスト容易性と予測可能性を最大化する。

### 1.2 具体的ルール

- **純粋関数を優先する**: ビジネスロジックは、外部状態（DB, Redis, ファイルシステム等）に依存しない純粋関数として実装する。入力のみから決定論的に出力を生成する `f: Input -> Output` の形式を厳守する。
- **副作用の分離**: I/O操作（DB保存、メッセージ送信、API呼び出し等）はビジネスロジックから明確に分離し、アプリケーション層やインフラ層に閉じ込める。ドメイン層には副作用を持ち込まない。
- **高階関数・合成の活用**: LINQ、`Select`、`Aggregate`、`Where` 等の関数合成を積極的に活用し、命令的なループや状態変数の使用を避ける。
- **静的メソッドの活用**: ドメインロジックは `static class` の `static` メソッドとして実装し、インスタンス状態への依存を排除する。

### 1.3 適用例

```csharp
// 良い例: 純粋関数として実装
public static class AccountCalculator
{
    public static AccountSummary Calculate(
        Guid contractId,
        IEnumerable<Determination> determinations,
        IEnumerable<Payment> payments)
    {
        var totalBilled = determinations.Sum(d => d.Amount);
        var totalPaid = payments.Sum(p => p.Amount);
        var balance = totalBilled - totalPaid;
        return new AccountSummary(contractId, balance, totalBilled, totalPaid);
    }
}

// 悪い例: 外部状態に依存
public class AccountCalculator
{
    private readonly IDbContext _db; // NG: 外部依存
    public AccountSummary Calculate(Guid contractId)
    {
        var determinations = _db.Determinations.Where(...); // NG: I/O混在
        ...
    }
}
```

---

## 2. テスト駆動開発（Test-Driven Development）

### 2.1 基本方針

すべての機能実装はテスト駆動開発（TDD）のサイクルに従って行う。テストなきコードのマージは禁止する。

### 2.2 TDDサイクル

1. **Red**: 実装前に、期待する振る舞いを定義するテストを書く（テストは失敗する）
2. **Green**: テストを通過する最小限の実装を行う
3. **Refactor**: テストが通る状態を維持しながら、コードを改善する

### 2.3 テスト規約

- **命名規則**: `[対象メソッド/シナリオ]_Should_[期待する振る舞い]` の形式で命名する
  - 例: `Initial_State_Should_Be_Zero`、`Regular_Billing_Should_Increase_Balance`
- **構造**: Arrange-Act-Assert（AAA）パターンを厳守する
- **テストの独立性**: 各テストは他のテストに依存せず、単独で実行可能であること
- **テストデータ**: テスト内でデータを完結させ、共有状態やDBアクセスを排除する
- **カバレッジ対象**:
  - ドメインロジック（課金計算、残高算出、ステータス判定）: 必須
  - 境界値（ゼロ、負数、最大値）: 必須
  - 異常系（不正入力、空コレクション）: 必須
  - API エンドポイント: 統合テストとして実装

### 2.4 適用例

```csharp
// TDDサイクルの Red フェーズで先に書くテスト
[Fact]
public void Overpayment_Should_Result_In_Negative_Balance()
{
    // Arrange
    var determinations = new[]
    {
        new Determination(Guid.NewGuid(), _contractId,
            DateTimeOffset.Now, DeterminationType.Regular, 1000m, "Monthly Fee")
    };
    var payments = new[]
    {
        new Payment(Guid.NewGuid(), _contractId,
            DateTimeOffset.Now, 1500m, "BankTransfer")
    };

    // Act
    var summary = AccountCalculator.Calculate(_contractId, determinations, payments);

    // Assert
    Assert.Equal(-500m, summary.ReceivableBalance);
    Assert.Equal(AccountStatus.Overpaid, summary.Status);
}
```

---

## 3. 不変性を意識したデータモデリング（Immutable Data Modeling）

### 3.1 基本方針

すべてのドメインモデルは不変（Immutable）として設計する。状態の変更は既存データの書き換えではなく、新しいレコードの追加によって表現する。

### 3.2 具体的ルール

- **`record` 型の使用**: ドメインモデルは C# の `record` 型（Positional Record）で定義し、コンパイラレベルで不変性を保証する。`class` でのミュータブルなモデル定義は禁止する。
- **Update/Delete の禁止**: データベース上の既存レコードに対する `UPDATE` / `DELETE` 操作は禁止する。すべての状態変化は `INSERT`（新しいレコードの追加）で表現する。
- **State derived from Events**: 「現在の状態」はカラムとして永続化せず、不変な履歴レコードの畳み込み（`Aggregate` / `Fold`）によって都度算出する。
- **スナップショットの保持**: 計算根拠（トラフィック量、適用単価等）は、調定レコードの `Snapshot` フィールドにJSON等で保持し、事後検証を可能にする。
- **`with` 式の活用**: レコードの派生が必要な場合は `with` 式を使用し、元のインスタンスを変更しない。

### 3.3 適用例

```csharp
// 良い例: record 型による不変モデル
public record Determination(
    Guid Id,
    Guid ContractId,
    DateTimeOffset HappenedAt,
    DeterminationType Type,
    decimal Amount,
    string Reason,
    object? Snapshot = null
);

// 良い例: with 式による派生
var original = new Determination(...);
var corrected = original with { Amount = -200m, Type = DeterminationType.Correction };

// 悪い例: ミュータブルなクラス
public class Determination
{
    public decimal Amount { get; set; } // NG: setter による変更可能
    public void UpdateAmount(decimal newAmount) { Amount = newAmount; } // NG: 破壊的変更
}
```

---

## 4. 遵守の確認

- コードレビュー時に本ガイドラインへの準拠を確認する
- AIエージェントによるコード生成時も本ガイドラインを参照し、準拠した実装を行う
- ガイドラインからの逸脱が必要な場合は、理由をコメントまたはコミットメッセージに明記する

---

## 5. AIエージェントによる実装方針

AIエージェントがコードの修正や生成を行う際は、以下の行動指針を遵守すること。

- **フォールバック不要**: 既存のコードへのフォールバック（以前のバージョンに戻すような提案や、安全策としての冗長な代替案の提示など）は原則不要とする。既存コードの維持よりも、ガイドラインに即した理想的な状態へのリファクタリングを優先する。
- **最善の実装を提案**: 常に本ガイドライン（関数型、不変性、TDD）に則った最善の実装を提案・適用すること。「とりあえず動く」コードではなく、「正しく設計された」コードを目指す。
- **明確な意図**: 自信がない場合の曖昧な修正よりも、明確な意図を持った修正を行うこと。なぜその修正が必要なのか、どのガイドラインに基づいているのかを論理的に説明できる変更を行う。
