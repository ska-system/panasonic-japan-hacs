# Panasonic Japan スマート家電 Home Assistant インテグレーション

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | 日本語

本カスタムインテグレーションは、CLUB Panasonic / キッチンポケット（Kitchen Pocket）クラウドサービスに連携した **Panasonic 日本国内向けスマート家電** を Home Assistant に統合・監視・操作するためのコンポーネントです。

> [!NOTE]
> 現在は主に **Panasonic製スマート冷蔵庫**（**NR-F607HPX-N** およびキッチンポケット対応の同系統モデル）を対象に設計・動作確認されています。

### 謝辞
本リポジトリは [yuyuvn/panasonic-japan-hacs](https://github.com/yuyuvn/panasonic-japan-hacs) の素晴らしい初期実装をベースに機能強化・フォークしたものです。Home Assistant 最新標準（`ConfigEntry.runtime_data`）への移行、日英完全対訳、クーリングアシストの疎結合化・状態管理、専用 Lovelace UI カード、ドア開閉履歴の取得、堅牢な自動再認証などを拡張しています。

---

## 主な機能

- **電気代削減額（エコナビ）の可視化**: 日々のエコナビ運転や省エネによる推定電気代削減額（円）、前月・前年同月との比較データを取得。
- **きめ細やかな庫内・温度制御**: 冷蔵室・冷凍室・パーシャル/チルド切替室の温度設定や庫内灯、ナノイーX、製氷モードの操作。
- **クーリングアシスト（CoolOven）の完全制御**: 「冷ます（quench）」「急冷（cold）」「急凍（frozen）」のモード切替、分単位・秒単位の時間設定、実行トリガー。
- **専用 Lovelace カスタムカード**: クーリングアシストを直感的に操作できるダッシュボードカード（`panasonic-cooloven-card`）を同梱・自動ロード。
- **Climate エンティティ対応**: 冷蔵庫全体を Climate エンティティとして公開し、プリセットモード（Preset Mode）として急冷・急凍を操作可能。
- **リアルタイム Push 通知（FCM）**: ドア開通知、製氷用給水タンクの給水不足、製氷完了、エラー発生、クーリングアシスト完了などをリアルタイムに HA イベントとして受信。
- **ドア開閉履歴・統計**: 本日のドア開閉回数センサー、過去1週間の履歴リスト、週平均開閉回数の属性保持。
- **堅牢な認証と再認証（Reauth）**: Auth0 PKCE OAuth2 フローによる安全な認証、トークン自動更新、認証失効時のワンクリック再認証。

---

## インストール方法

### HACS によるインストール（推奨）

1. Home Assistant の **HACS** を開きます。
2. **インテグレーション（Integrations）** 画面を開き、右上の三点リーダー（⋮）→ **カスタムリポジトリ（Custom repositories）** をクリックします。
3. リポジトリ URL に `https://github.com/ska-system/panasonic-japan-hacs` を入力します。
4. カテゴリで **インテグレーション（Integration）** を選択し、**追加（Add）** をクリックします。
5. 一覧から **Panasonic Japan** を検索して **ダウンロード（Download）** を行います。
6. Home Assistant を再起動します。

### 手動インストール

1. リポジトリから最新のソースコードをダウンロードします。
2. `custom_components/panasonic_japan` フォルダを、Home Assistant の `<config_dir>/custom_components/` ディレクトリ内にコピーします。
3. Home Assistant を再起動します。

---

## 初期設定（Auth0 PKCE 認証フロー）

1. Home Assistant の **設定** → **デバイスとサービス** → **インテグレーションを追加** を開きます。
2. **Panasonic Japan** を検索して選択します。
3. ログイン用の URL が生成されます。リンクをクリックするか URL をブラウザで開きます。
4. CLUB Panasonic アカウントでログインします。
5. ログイン完了後、ブラウザが `com.panasonic.jp.kitchenpocket.auth0://...` から始まるコールバック URL にリダイレクトされます。
   > [!TIP]
   > ブラウザ上でリダイレクト先が開かず白い画面や接続エラーが表示される場合は、ブラウザの開発者ツール（<kbd>F12</kbd> または右クリック → 検証）を開き、**ネットワーク** タブやアドレスバーからリダイレクト先の URL 全体をコピーしてください。
6. コピーしたコールバック URL 全体を Home Assistant の入力欄に貼り付けて送信します。
7. アカウント識別名（複数アカウント管理用、例: `自宅の冷蔵庫` など）を入力して完了します。

### 再認証（Reauth）について
万が一リフレッシュトークンの期限切れや失効が発生した場合は、Home Assistant 画面上に自動的に **再認証** の通知が表示されます。既存のエンティティIDやダッシュボード設定を維持したまま、ワンクリックで再ログインが可能です。

---

## Lovelace カスタムカード

本インテグレーションには、クーリングアシスト操作用のカスタムカードが同梱されています。リソースは `/panasonic_japan_assets/panasonic-cooloven-card.js` に自動登録されます。

### ダッシュボードへの配置例

ダッシュボードの編集画面で **手動カード（Manual Card）** を追加します：

```yaml
type: custom:panasonic-cooloven-card
entity: climate.panasonic_fridge_nr_f607hpx_n
```

---

## エンティティ・コントロール一覧

### 1. Climate エンティティ
| エンティティ ID | 説明 | 機能・プリセット |
|---|---|---|
| `climate.<appliance_id>_climate` | 冷蔵庫本体 Climate エンティティ | 運転モード: `auto`<br>プリセットモード: `off`（オフ）, `quench`（冷ます）, `cold`（急冷）, `frozen`（急凍）<br>専用サービス: `climate.cooling_assist` |

### 2. センサー（Sensor）
| エンティティ ID | 名称 | 単位 | 属性 / 説明 |
|---|---|---|---|
| `sensor.<appliance_id>_cost_reduction` | 電気代削減額 | `yen` | 推定削減額（`last_month_reduction`: 前月削減額, `last_year_reduction`: 前年同月削減額） |
| `sensor.<appliance_id>_operation_mode` | 運転モード | — | 運転状態（`winter_setting`: 冬季設定, `house_sitting`: 留守番, `pre_cooling`: 予冷, `outage_prepare`: 停電準備） |
| `sensor.<appliance_id>_firmware_version` | ファームウェアバージョン | — | ファームウェア情報（`latest_version`: 最新バージョン, `update_status`: 更新状態） |
| `sensor.<appliance_id>_cooloven_state` | クーリングアシスト状態 | — | 動作中のクーリングアシストモード（`off`, `quench`, `cold`, `frozen`） |
| `sensor.<appliance_id>_door_open_count` | ドア開閉回数 | `回` | 本日のドア開閉回数（`weekly_door_open_list`: 過去1週間の日別開閉回数, `average_open_count`: 週平均開閉回数） |

### 3. セレクト（Select - 各種モード・庫内灯設定）
| エンティティ ID | 名称 | 選択肢 |
|---|---|---|
| `select.<appliance_id>_partial_mode` | パーシャル/チルド切替 | `chilled`（チルド）, `weak`（パーシャル 弱）, `medium`（パーシャル 中）, `strong`（パーシャル 強） |
| `select.<appliance_id>_cold_room_mode` | 冷蔵 | `weak`（弱）, `medium`（中）, `strong`（強） |
| `select.<appliance_id>_freezing_room_mode` | 冷凍 | `weak`（弱）, `medium`（中）, `strong`（強） |
| `select.<appliance_id>_coldroom_light_mode` | 冷蔵室庫内照明 | `off`（切）, `dark`（暗）, `bright`（明） |
| `select.<appliance_id>_pcroom_light_mode` | パーシャル/チルド切替室照明 | `off`（切）, `dark`（暗）, `bright`（明） |
| `select.<appliance_id>_cooloven_lamp_mode` | 「クーリングアシスト」ランプ表示 | `off`（切）, `dark`（暗）, `bright`（明） |
| `select.<appliance_id>_door_alarms_mode` | ドアアラーム音量 | `medium`（中）, `big`（大） |
| `select.<appliance_id>_ice_making_mode` | 製氷モード | `quick`（速氷）, `stop`（停止）, `normal`（通常） |
| `select.<appliance_id>_nanoex` | ナノイーX | `on`（入）, `off`（切）, `clean`（クリーン） |
| `select.<appliance_id>_cooling_assist_mode` | クーリングアシスト モード | `off`（オフ）, `quench`（冷ます）, `cold`（急冷）, `frozen`（急凍） |

### 4. ナンバー（Number - 時間設定）
| エンティティ ID | 名称 | 範囲 | 刻み | 説明 |
|---|---|---|---|---|
| `number.<appliance_id>_cooling_assist_time` | クーリングアシスト 時間 | 0 ～ 60 分 | 1 分 | クーリングアシストの運転分数（モードにより上限・下限が自動連動） |
| `number.<appliance_id>_cooling_assist_second` | クーリングアシスト 秒 | 0 ～ 50 秒 | 10 秒 | クーリングアシストの運転秒数（「冷ます」モードで使用） |
| `number.<appliance_id>_notify_door_open_time` | 通知設定：ドアモニター時間 | 0 ～ 72 時間 | 1 時間 | ドア開放警告通知が飛ぶまでの閾値時間設定 |

### 5. スイッチ（Switch）
| エンティティ ID | 名称 | カテゴリ | 説明 |
|---|---|---|---|
| `switch.<appliance_id>_fast_ice` | 速氷 | 制御 | 急速製氷の ON / OFF |
| `switch.<appliance_id>_stop_ice` | 製氷停止 | 制御 | 自動製氷の停止 ON / OFF |
| `switch.<appliance_id>_fresh_frozen` | 新鮮凍結 | 制御 | 新鮮凍結運転の ON / OFF |
| `switch.<appliance_id>_econavi_lamp` | 「エコナビ」ランプ表示 | 制御 | 本体のエコナビランプ点灯 ON / OFF |
| `switch.<appliance_id>_notify_water_shortage` | 通知設定：給水不足 | 設定 | 給水タンクが空になった際のプッシュ通知 ON / OFF |
| `switch.<appliance_id>_notify_cool_oven` | 通知設定：クーリングアシスト | 設定 | クーリングアシスト完了時のプッシュ通知 ON / OFF |
| `switch.<appliance_id>_notify_ice_completed` | 通知設定：製氷完了 | 設定 | 製氷完了時のプッシュ通知 ON / OFF |
| `switch.<appliance_id>_notify_error_occurred` | 通知設定：エラー発生 | 設定 | 機器エラー発生時のプッシュ通知 ON / OFF |
| `switch.<appliance_id>_notify_door_open` | 通知設定：ドアモニター | 設定 | ドア開通知のプッシュ通知 ON / OFF |

### 6. ボタン（Button）
| エンティティ ID | 名称 | 説明 |
|---|---|---|
| `button.<appliance_id>_cooling_assist` | クーリングアシスト実行 | `select.cooling_assist_mode`, `number.cooling_assist_time`, `number.cooling_assist_second` で設定されている内容でクーリングアシストを実行します |

---

## サービス（Services）

### `panasonic_japan.set_cooloven`
対象の冷蔵庫に対してクーリングアシストを実行します。

```yaml
service: panasonic_japan.set_cooloven
data:
  mode: quench       # off, quench, cold, frozen
  time: 5            # 分（0 - 60）
  second: 30         # 秒（0 - 50、10秒刻み）
  appliance_id: "your_appliance_id"  # 1台のみの場合は省略可能
```

### `climate.cooling_assist`
`climate.<appliance_id>_climate` エンティティを対象にクーリングアシストを実行します。

```yaml
service: climate.cooling_assist
target:
  entity_id: climate.panasonic_fridge_nr_f607hpx_n
data:
  mode: cold
  time: 15
```

---

## プッシュ通知イベント（FCM Push）

Panasonic のクラウドサーバーからプッシュ通知を受信した際、Home Assistant のイベントバスに以下のイベントを発行します：

| イベント名 | 発行契機 | ペイロード項目 |
|---|---|---|
| `panasonic_japan_door_event` | ドアが一定時間以上開いたまま | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_water_shortage_event` | 製氷用給水タンクの水切れ | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_ice_completed_event` | 製氷が完了 | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_error_event` | 機器のエラー・自己診断通知 | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_cooloven_completed_event` | クーリングアシストが完了 | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_cooloven_canceled_event` | クーリングアシストが途中でキャンセル | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_cooloven_changed_event` | クーリングアシストの設定が変更 | `appliance_id`, `title`, `body`, `kind` |
| `panasonic_japan_push_event` | その他の汎用プッシュ通知 | `appliance_id`, `title`, `body`, `kind` |

### オートメーション例：ドア開放の通知とスマートスピーカー連携

```yaml
alias: "冷蔵庫ドア開放通知"
description: "ドアが開いたままのときにスマホやスマートスピーカーに通知"
trigger:
  - trigger: event
    event_type: panasonic_japan_door_event
action:
  - action: notify.persistent_notification
    data:
      title: "{{ trigger.event.data.title }}"
      message: "{{ trigger.event.data.body }}"
```

---

## 動作環境

- Home Assistant 2024.x 以降（2024.x ～ 2026.x で検証済み）
- Python 3.10 以降
- CLUB Panasonic / キッチンポケットに登録済みの対象スマート家電

---

## ライセンス

本プロジェクトは [MIT License](LICENSE) の下で公開されています。
