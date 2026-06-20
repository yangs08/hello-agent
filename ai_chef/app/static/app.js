const { createApp, nextTick } = Vue;

createApp({
  data() {
    return {
      sessionId: this.createSessionId(),
      draft: "",
      imageFile: null,
      imagePreview: "",
      messages: [],
      isSending: false,
      typingQueues: {},
      typingTimers: {},
      typingResolvers: {},
    };
  },
  computed: {
    canSend() {
      return this.draft.trim().length > 0 || Boolean(this.imageFile);
    },
    showLoading() {
      const lastMessage = this.messages[this.messages.length - 1];
      return this.isSending && (!lastMessage || lastMessage.role !== "assistant");
    },
  },
  methods: {
    createSessionId() {
      if (crypto.randomUUID) {
        return `session-${crypto.randomUUID()}`;
      }
      return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    },
    newSession() {
      this.clearAllTyping();
      this.sessionId = this.createSessionId();
      this.draft = "";
      this.clearImage();
      this.messages = [];
    },
    openFilePicker() {
      this.$refs.fileInput.click();
    },
    selectImage(event) {
      const [file] = event.target.files;
      if (!file) return;

      if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
        this.addAssistantMessage("请上传 JPG、PNG 或 WebP 格式的图片。");
        event.target.value = "";
        return;
      }

      this.imageFile = file;
      this.imagePreview = URL.createObjectURL(file);
    },
    clearImage() {
      if (this.imagePreview) {
        URL.revokeObjectURL(this.imagePreview);
      }
      this.imageFile = null;
      this.imagePreview = "";
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = "";
      }
    },
    addAssistantMessage(text) {
      const message = {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        role: "assistant",
        text,
      };
      this.messages.push(message);
      this.scrollToBottom();
      return this.messages[this.messages.length - 1];
    },
    appendAssistantText(message, text) {
      if (!text) return;

      if (!this.typingQueues[message.id]) {
        this.typingQueues[message.id] = "";
      }
      this.typingQueues[message.id] += text;
      this.startTyping(message);
    },
    startTyping(message) {
      if (this.typingTimers[message.id]) return;

      this.typingTimers[message.id] = window.setInterval(() => {
        const queue = this.typingQueues[message.id] || "";
        if (!queue) {
          window.clearInterval(this.typingTimers[message.id]);
          delete this.typingTimers[message.id];
          this.resolveTyping(message.id);
          return;
        }

        const nextChar = queue.slice(0, 1);
        this.typingQueues[message.id] = queue.slice(1);
        message.text += nextChar;
        this.scrollToBottom();
      }, 22);
    },
    waitForTyping(message) {
      if (!message) return Promise.resolve();
      if (!this.typingQueues[message.id] && !this.typingTimers[message.id]) {
        return Promise.resolve();
      }

      return new Promise((resolve) => {
        this.typingResolvers[message.id] = resolve;
      });
    },
    resolveTyping(messageId) {
      const resolve = this.typingResolvers[messageId];
      if (resolve) {
        resolve();
        delete this.typingResolvers[messageId];
      }
      delete this.typingQueues[messageId];
    },
    async uploadImage() {
      if (!this.imageFile) return null;

      const form = new FormData();
      form.append("session_id", this.sessionId);
      form.append("file", this.imageFile);

      const response = await fetch("/uploads", {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "图片上传失败");
      }

      const data = await response.json();
      return new URL(data.url, window.location.origin).href;
    },
    buildMessagePayload(text, imageUrl) {
      if (!imageUrl) {
        return text;
      }

      const content = [];
      if (text) {
        content.push({ type: "text", text });
      } else {
        content.push({ type: "text", text: "请根据这张图片给我私厨建议" });
      }
      content.push({ type: "image", url: imageUrl });
      return content;
    },
    async sendMessage() {
      if (!this.canSend || this.isSending) return;

      const text = this.draft.trim();
      const imagePreview = this.imagePreview;
      const imageFile = this.imageFile;

      this.messages.push({
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        role: "user",
        text: text || "请根据这张图片给我私厨建议",
        imagePreview,
      });

      this.draft = "";
      this.imageFile = null;
      this.imagePreview = "";
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = "";
      }
      this.isSending = true;
      this.scrollToBottom();
      let assistantMessage = null;

      try {
        let imageUrl = null;
        if (imageFile) {
          this.imageFile = imageFile;
          imageUrl = await this.uploadImage();
          this.imageFile = null;
        }

        assistantMessage = this.addAssistantMessage("");
        const response = await fetch("/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: this.sessionId,
            message: this.buildMessagePayload(text, imageUrl),
          }),
        });

        if (!response.ok) {
          const detail = await response.text();
          throw new Error(detail || "私厨暂时没有回应");
        }

        await this.readChatStream(response, assistantMessage);
        await this.waitForTyping(assistantMessage);
      } catch (error) {
        const message = error.message || "请求失败，请稍后再试。";
        if (assistantMessage) {
          this.clearTyping(assistantMessage.id);
          assistantMessage.text = message;
        } else {
          this.addAssistantMessage(message);
        }
      } finally {
        this.isSending = false;
        this.scrollToBottom();
      }
    },
    clearTyping(messageId) {
      if (this.typingTimers[messageId]) {
        window.clearInterval(this.typingTimers[messageId]);
        delete this.typingTimers[messageId];
      }
      delete this.typingQueues[messageId];
      this.resolveTyping(messageId);
    },
    clearAllTyping() {
      for (const messageId of Object.keys(this.typingTimers)) {
        this.clearTyping(messageId);
      }
      for (const messageId of Object.keys(this.typingQueues)) {
        this.clearTyping(messageId);
      }
    },
    async readChatStream(response, assistantMessage) {
      if (!response.body) {
        throw new Error("当前浏览器不支持流式响应");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventText of events) {
          this.handleStreamEvent(eventText, assistantMessage);
        }
      }

      if (buffer.trim()) {
        this.handleStreamEvent(buffer, assistantMessage);
      }
    },
    handleStreamEvent(eventText, assistantMessage) {
      const lines = eventText.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event:"));
      const dataLine = lines.find((line) => line.startsWith("data:"));
      const eventName = eventLine ? eventLine.slice(6).trim() : "message";
      const dataText = dataLine ? dataLine.slice(5).trim() : "{}";
      const data = JSON.parse(dataText);

      if (eventName === "delta") {
        this.appendAssistantText(assistantMessage, data.text || "");
      } else if (eventName === "error") {
        throw new Error(data.message || "私厨暂时没有回应");
      }
    },
    async scrollToBottom() {
      await nextTick();
      const el = this.$refs.conversationEl;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    },
  },
}).mount("#app");
