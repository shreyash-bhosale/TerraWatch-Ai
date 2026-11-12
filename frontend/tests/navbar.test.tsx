import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Navbar } from '@/components/Navbar'

vi.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
}))

describe('Navbar', () => {
  it('renders a keyboard-operable mobile menu toggle and closes on Escape', () => {
    render(<Navbar />)

    const toggle = screen.getByRole('button', { name: /toggle navigation menu/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    const mobileNav = screen.getByRole('navigation', { name: /mobile navigation/i })
    expect(mobileNav).toBeInTheDocument()

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
  })
})

