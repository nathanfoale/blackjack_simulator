
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import random

st.set_page_config(
    page_title="Blackjack Simulator",
    layout="centered",  # switch from "wide" to "centered"
    initial_sidebar_state="expanded"
)

# Optional: CSS tweaks for mobile
st.markdown("""
    <style>
        @media (max-width: 768px) {
            h1 { font-size: 1.5em; }
            .block-container {
                padding: 1rem 1rem;
            }
        }
        .stSlider > div[data-baseweb="slider"] {
            padding: 6px 0;
        }
    </style>
""", unsafe_allow_html=True)

# === Sidebar Parameters ===
initial_bankroll = st.sidebar.number_input("Initial Bankroll ($)", 1000, 1000000, 100000, step=1000)
min_bet = st.sidebar.number_input("Minimum Bet ($)", 10, 500, 100, step=10)
spread = st.sidebar.slider("Bet Spread (Hi-Lo Count Multiplier)", 1, 20, 10)
num_simulations = st.sidebar.slider("Number of Simulations", 1, 500, 100)
num_hands = st.sidebar.slider("Hands per Simulation", 100, 10000, 2000, step=100)
num_decks = st.sidebar.slider("Number of Decks", 1, 8, 8)
blackjack_payout = st.sidebar.selectbox("Blackjack Payout", ["3:2", "6:5"])
enable_surrender = st.sidebar.checkbox("Allow Surrender", value=True)

# === Hi-Lo Card Values ===
card_values = {
    '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
    '7': 0, '8': 0, '9': 0,
    '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
}
cards = list(card_values.keys()) * 4 * num_decks

def get_true_count(running_count, decks_remaining):
    return running_count / decks_remaining if decks_remaining > 0 else 0

def simulate_single_run():
    deck = cards.copy()
    random.shuffle(deck)
    running_count = 0
    bankroll = initial_bankroll
    bankrolls = []

    for _ in range(num_hands):
        if len(deck) < 52:
            deck = cards.copy()
            random.shuffle(deck)
            running_count = 0

        card = deck.pop()
        running_count += card_values[card]
        true_count = get_true_count(running_count, len(deck) / 52)

        bet = min_bet
        if true_count > 1:
            bet *= min(spread, int(true_count))
        bet = min(bankroll, bet)

        # Estimate probabilities based on card counting advantage
        edge = 0.005 + (0.005 * true_count)  # up to ~+3% edge
        win_prob = min(0.44 + edge, 0.51)
        lose_prob = max(0.44 - edge, 0.38)
        push_prob = 1.0 - win_prob - lose_prob

        total = win_prob + lose_prob + push_prob
        win_prob /= total
        lose_prob /= total
        push_prob = 1.0 - win_prob - lose_prob

        outcome = np.random.choice(["win", "lose", "push"], p=[win_prob, lose_prob, push_prob])
        if outcome == "win":
            if np.random.rand() < 0.05:  # chance of blackjack
                payout = 1.5 if blackjack_payout == "3:2" else 1.2
                bankroll += bet * payout
            else:
                bankroll += bet
        elif outcome == "lose":
            if enable_surrender and np.random.rand() < 0.05:  # small chance of surrender
                bankroll -= bet / 2
            else:
                bankroll -= bet
        # push: bankroll unchanged

        bankrolls.append(bankroll)
        if bankroll <= 0:
            break

    return bankrolls

# === Run Simulations ===
with st.spinner("Simulating Blackjack hands..."):
    all_results = [simulate_single_run() for _ in range(num_simulations)]

max_length = max(len(r) for r in all_results)
padded_results = [r + [r[-1]] * (max_length - len(r)) for r in all_results]
array_results = np.array(padded_results)

avg_bankroll = np.mean(array_results, axis=0)
final_bankrolls = array_results[:, -1]
roi = ((final_bankrolls.mean() - initial_bankroll) / initial_bankroll) * 100
risk_of_ruin = np.mean(final_bankrolls <= 0) * 100
std_dev = np.std(final_bankrolls)

# === Plot with Plotly ===
fig = go.Figure()
for run in array_results[:20]:
    fig.add_trace(go.Scatter(y=run, mode='lines', line=dict(width=1), opacity=0.15, showlegend=False))
fig.add_trace(go.Scatter(y=avg_bankroll, mode='lines', name='Average Bankroll', line=dict(color='blue', width=4)))
fig.add_trace(go.Scatter(y=[initial_bankroll] * max_length, mode='lines', name='Initial Bankroll',
                         line=dict(dash='dash', color='black')))
fig.update_layout(title="💰 Blackjack Bankroll Simulation",
                  xaxis_title="Hands Played",
                  yaxis_title="Bankroll ($)",
                  height=500)
st.plotly_chart(fig, use_container_width=True)

# === Results Summary ===
st.subheader("📊 Simulation Results")
col1, col2, col3, col4 = st.columns(4)
col1.metric("💸 Final Avg Bankroll", f"${final_bankrolls.mean():,.0f}")
col2.metric("📉 Std Dev", f"${std_dev:,.0f}")
col3.metric("📈 ROI", f"{roi:.2f}%", delta_color="normal")
col4.metric("⚠️ Risk of Ruin", f"{risk_of_ruin:.2f}%")

# === Histogram of Final Bankrolls ===
st.subheader("📉 Distribution of Final Bankrolls")
hist_fig = go.Figure()
hist_fig.add_trace(go.Histogram(x=final_bankrolls, nbinsx=40, marker_color='green'))
hist_fig.update_layout(bargap=0.1, xaxis_title="Final Bankroll", yaxis_title="Frequency", height=400)
st.plotly_chart(hist_fig, use_container_width=True)

