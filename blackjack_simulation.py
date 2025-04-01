import streamlit as st
import plotly.graph_objects as go
import numpy as np
import random

# === Streamlit Setup ===
st.set_page_config(page_title="Blackjack Card Counting Simulator", layout="wide")
st.title("🃏 Blackjack Simulation with Card Counting (8 Decks)")

# === Mobile Optimization CSS ===
st.markdown("""
    <style>
        @media only screen and (max-width: 600px) {
            .element-container {
                padding-left: 5px !important;
                padding-right: 5px !important;
            }
            .block-container {
                padding-left: 10px !important;
                padding-right: 10px !important;
            }
            canvas {
                width: 100% !important;
                height: auto !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

# === Parameters ===
initial_bankroll = st.sidebar.number_input("Initial Bankroll ($)", 1000, 1000000, 1000000, step=1000)
min_bet = st.sidebar.number_input("Minimum Bet ($)", 10, 500, 100, step=10)
spread = st.sidebar.slider("Bet Spread (for Hi-Lo Count)", 1, 20, 10)
num_simulations = st.sidebar.slider("Number of Simulations", 1, 500, 100)
num_hands = st.sidebar.slider("Hands per Simulation", 100, 20000, 10000, step=100)
num_decks = st.sidebar.slider("Number of Decks", 1, 8, 8)

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

        # Slight player edge when true count is high
        win_prob = 0.48 + min(0.01 * max(0, true_count - 1), 0.05)  # Max edge boost ~5%
        lose_prob = 1 - win_prob - 0.08  # push ~8%
        push_prob = 0.08

        # Safety correction
        if win_prob + lose_prob + push_prob != 1.0:
            delta = 1.0 - (win_prob + lose_prob + push_prob)
            lose_prob += delta  # minor fix

        outcome = np.random.choice(["win", "lose", "push"], p=[win_prob, lose_prob, push_prob])
        if outcome == "win":
            bankroll += bet * 1.5  # includes blackjack payout approximation
        elif outcome == "lose":
            bankroll -= bet

        bankrolls.append(bankroll)

        if bankroll <= 0:
            break

    return bankrolls

# === Run Simulations ===
all_results = [simulate_single_run() for _ in range(num_simulations)]
max_length = max(len(r) for r in all_results)
padded_results = [r + [r[-1]] * (max_length - len(r)) for r in all_results]
array_results = np.array(padded_results)

avg_bankroll = np.mean(array_results, axis=0)
std_dev = np.std(array_results[:, -1])
final_bankrolls = array_results[:, -1]
roi = ((final_bankrolls.mean() - initial_bankroll) / initial_bankroll) * 100
risk_of_ruin = np.mean(final_bankrolls <= 0) * 100

# === Plotly Graph ===
fig = go.Figure()

# Lighter traces for individual runs
for run in array_results:
    fig.add_trace(go.Scatter(y=run, mode='lines', line=dict(color='gray', width=1), opacity=0.2, showlegend=False))

# Average line
fig.add_trace(go.Scatter(y=avg_bankroll, mode='lines', name='Average Bankroll',
                         line=dict(color='blue', width=3)))

# Horizontal initial bankroll line
fig.add_shape(type='line', x0=0, x1=max_length, y0=initial_bankroll, y1=initial_bankroll,
              line=dict(color='black', dash='dash'), name="Initial Bankroll")

fig.update_layout(
    title="📈 Bankroll Trajectory Over Time",
    xaxis_title="Hand Number",
    yaxis_title="Bankroll ($)",
    dragmode=False,
    hovermode="x unified",
    height=500,
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)

# Show chart
st.plotly_chart(fig, use_container_width=True, config={"responsive": True, "scrollZoom": False})

# === Summary ===
st.subheader("📊 Simulation Results Summary")
st.metric("Final Average Bankroll", f"${final_bankrolls.mean():,.0f}")
st.metric("Standard Deviation", f"${std_dev:,.0f}")
st.metric("Return on Investment (ROI)", f"{roi:.2f}%")
st.metric("Risk of Ruin", f"{risk_of_ruin:.2f}%")

# === Histogram of Final Bankrolls ===
st.subheader("📉 Distribution of Final Bankrolls")
hist_fig = go.Figure()
hist_fig.add_trace(go.Histogram(x=final_bankrolls, nbinsx=40, marker_color='green'))
hist_fig.update_layout(bargap=0.1, xaxis_title="Final Bankroll", yaxis_title="Frequency", height=400)
st.plotly_chart(hist_fig, use_container_width=True)
