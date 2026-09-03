import { useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './App.css'

gsap.registerPlugin(ScrollTrigger)

function App() {
  const page = useRef()
  const button = useRef()
  const chatInput = useRef()

  const [chatOpen, setChatOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

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

    try {
      const response = await fetch('/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: cleanQuestion,
          conversation: previousMessages.slice(-10),
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.answer || 'Request failed')
      }

      const aiMessage = {
        role: 'assistant',
        content: data.answer,
      }

      setMessages([...previousMessages, userMessage, aiMessage])
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

              <button className="close-chat" onClick={closeChat}>
                ×
              </button>
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

              {loading && (
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