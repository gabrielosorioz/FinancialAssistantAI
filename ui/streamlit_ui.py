import streamlit as st

class ExpenseClassifierUI:
    def __init__(self, classifier, feedback_agent):
        self.feedback_agent = feedback_agent
        self.classifier = classifier

    def run(self):
        """Executa a interface gráfica"""
        st.title("💬 Chat de Classificação de Despesas")
        st.write("Insira uma descrição de despesa e o sistema classificará a categoria.")
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Digite a descrição da despesa..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            category = self.classifier.classify(prompt)
            feedback_message = self.feedback_agent.generate_feedback(prompt, category)
            st.session_state.messages.append({"role": "assistant", "content": feedback_message})

            with st.chat_message("assistant"):
                st.markdown(f"**{feedback_message}**")