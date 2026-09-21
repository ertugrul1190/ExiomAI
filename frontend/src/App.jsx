import { useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './App.css'

gsap.registerPlugin(ScrollTrigger)

const STREAMING_KEY = 'exiom.streaming'

function App() {
  const page = useRef()
  const button = useRef()
  const chatInput = useRef()

  const [chatOpen, setChatOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  // Text of the answer currently arriving, before it joins
  // the conversation as a finished message.
  const [live, setLive] = useState('')

  const [streaming, setStreaming] = useState(
    () => window.localStorage.getItem(STREAMING_KEY) !== 'off'
  )

  const toggleStreaming = () => {
    const next = !streaming

    setStreaming(next)

    window.localStorage.setItem(
      STREAMING_KEY,
      next ? 'on' : 'off'
    )
  }

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.brand, .creator', {
        opacity: 0,
        y: -20,
        duration: 0.9,
        ease: 'power3.out',
      })

      gsap.from('.orb', {
        opacity: 0,
        scale: 0.72,
        duration: 1.5,
        ease: 'power4.out',
      })

      gsap.from('.hero-title, .ask-button, .price', {
        opacity: 0,
        y: 35,
        duration: 1,
        stagger: 0.12,
        delay: 0.35,
        ease: 'power3.out',
      })

      gsap.to('.orb', {
        y: -13,
        duration: 2.7,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
      })
    }, page)

    return () => ctx.revert()
  }, [])

  const openChat = () => {
    const tl = gsap.timeline({
      onComplete: () => {
        setChatOpen(true)

        setTimeout(() => {
          gsap.fromTo(
            '.chat-shell',
            {
              opacity: 0,
              scale: 0.94,
              y: 35,
            },
            {
              opacity: 1,
              scale: 1,
              y: 0,
              duration: 0.8,
              ease: 'power4.out',
            }
          )

          chatInput.current?.focus()
        }, 30)
      },
    })

    tl.to('.orb', {
      scale: 1.7,
      opacity: 0,
      duration: 0.65,
      ease: 'power3.in',
    })

    tl.to(
      '.hero-title, .price',
      {
        opacity: 0,
        y: -35,
        duration: 0.35,
        ease: 'power2.in',
      },
      0
    )

    tl.to(
      '.ask-button',
      {
        scale: 1.12,
        opacity: 0,
        duration: 0.45,
        ease: 'power2.in',
      },
      0.1
    )
  }

  const closeChat = () => {
    gsap.to('.chat-shell', {
      opacity: 0,
      scale: 0.96,
      y: 25,
      duration: 0.35,
      ease: 'power2.in',
      onComplete: () => {
        setChatOpen(false)

        setTimeout(() => {
          gsap.to('.orb', {
            opacity: 1,
            scale: 1,
            duration: 0.8,
            ease: 'power4.out',
          })

          gsap.to('.hero-title, .price, .ask-button', {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.6,
            stagger: 0.06,
            ease: 'power3.out',
          })
        }, 20)
      },
    })
  }

  const askOnce = async (body) => {
    const response = await fetch('/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.answer || 'Request failed')
    }

    return data.answer
  }

  const askStreaming = async (body) => {
    const response = await fetch('/ask/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    // Anything refused before the stream opened is still an
    // ordinary JSON error, so it keeps its status code.
    if (!response.ok || !response.body) {
      const data = await response.json().catch(() => ({}))

      throw new Error(data.answer || 'Request failed')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    let buffer = ''
    let answer = ''

    const handle = (frame) => {
      if (frame.type === 'delta') {
        answer += frame.text
      } else if (frame.type === 'message') {
        answer = frame.answer
      } else if (frame.type === 'error') {
        answer = answer
          ? `${answer}\n\n${frame.answer}`
          : frame.answer
      }

      setLive(answer)
    }

    for (;;) {
      const { done, value } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // A frame is only complete once its blank line arrives;
      // whatever follows the last one stays buffered.
      const frames = buffer.split('\n\n')
      buffer = frames.pop()

      for (const frame of frames) {
        const line = frame
          .split('\n')
          .find((part) => part.startsWith('data: '))

        if (!line) continue

        try {
          handle(JSON.parse(line.slice(6)))
        } catch (error) {
          console.error('Bad stream frame', error)
        }
      }
    }

    return answer
  }

  const sendQuestion = async () => {
    const cleanQuestion = question.trim()

    if (!cleanQuestion || loading) return

    const previousMessages = [...messages]

    const userMessage = {
      role: 'user',
      content: cleanQuestion,
    }

    setMessages([...previousMessages, userMessage])
    setQuestion('')
    setLoading(true)
    setLive('')

    const body = {
      question: cleanQuestion,
      conversation: previousMessages.slice(-10),
    }

    try {
      const answer = streaming
        ? await askStreaming(body)
        : await askOnce(body)

      setMessages([
        ...previousMessages,
        userMessage,
        {
          role: 'assistant',
          content: answer,
        },
      ])
    } catch (error) {
      setMessages([
        ...previousMessages,
        userMessage,
        {
          role: 'assistant',
          content: 'EXIOM AI could not connect. Please try again.',
        },
      ])

      console.error(error)
    } finally {
      setLoading(false)
      setLive('')
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      sendQuestion()
    }
  }

  const moveButton = (event) => {
    if (window.matchMedia('(pointer: coarse)').matches) return

    const rect = button.current.getBoundingClientRect()
    const x = event.clientX - rect.left - rect.width / 2
    const y = event.clientY - rect.top - rect.height / 2

    gsap.to(button.current, {
      x: x * 0.12,
      y: y * 0.22,
      duration: 0.35,
      ease: 'power2.out',
    })
  }

  const resetButton = () => {
    gsap.to(button.current, {
      x: 0,
      y: 0,
      duration: 0.7,
      ease: 'elastic.out(1, 0.35)',
    })
  }

  return (
    <main className="exiom" ref={page}>
      <div className="ambient ambient-blue" />
      <div className="ambient ambient-orange" />

      <header>
        <div className="brand">
          <span className="brand-mark">X</span>
          <span>EXIOM AI</span>
        </div>

        <a className="creator" href="#" onClick={(e) => e.preventDefault()}>
          BY XRYPTO
        </a>
      </header>

      {!chatOpen ? (
        <section className="hero">
          <div className="orb">
            <div className="orb-core">X</div>
          </div>

          <h1 className="hero-title">
            EXIOM <span>AI</span>
          </h1>

          <button
            ref={button}
            className="ask-button"
            onMouseMove={moveButton}
            onMouseLeave={resetButton}
            onClick={openChat}
          >
            <span>START A CONVERSATION</span>
            <span className="arrow">↗</span>
          </button>

          <div className="price">
            <span>XEQM</span>
            <strong>$0.016</strong>
          </div>
        </section>
      ) : (
        <section className="chat-stage">
          <div className="chat-shell">

            <div className="chat-top">
              <div className="chat-identity">
                <span className="status-dot" />

                <div>
                  <strong>EXIOM AI</strong>
                  <span>ONLINE</span>
                </div>
              </div>

              <div className="chat-actions">
                <label
                  className={`stream-toggle ${loading ? 'is-locked' : ''}`}
                  title="Streaming responses"
                >
                  <input
                    type="checkbox"
                    checked={streaming}
                    onChange={toggleStreaming}
                    disabled={loading}
                    aria-label="Streaming responses"
                  />

                  <span className="stream-track">
                    <span className="stream-thumb" />
                  </span>

                  <span className="stream-name">STREAMING</span>
                </label>

                <button className="close-chat" onClick={closeChat}>
                  ×
                </button>
              </div>
            </div>

            <div className="messages">
              {messages.length === 0 && (
                <div className="chat-empty">
                  <div className="mini-core">X</div>

                  <h2>Ask EXIOM.</h2>
                </div>
              )}

              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`message ${message.role}`}
                >
                  <span>
                    {message.role === 'assistant' ? 'EXIOM' : 'YOU'}
                  </span>

                  <p>{message.content}</p>
                </div>
              ))}

              {live && (
                <div className="message assistant">
                  <span>EXIOM</span>

                  <p className="is-streaming">{live}</p>
                </div>
              )}

              {loading && !live && (
                <div className="message assistant">
                  <span>EXIOM</span>

                  <div className="thinking">
                    <i />
                    <i />
                    <i />
                  </div>
                </div>
              )}
            </div>

            <div className="chat-input-wrap">
              <textarea
                ref={chatInput}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about XEQM..."
                rows="1"
                maxLength="1000"
              />

              <button
                className="send-button"
                onClick={sendQuestion}
                disabled={loading}
              >
                ↑
              </button>
            </div>

          </div>
        </section>
      )}
    </main>
  )
}

export default App