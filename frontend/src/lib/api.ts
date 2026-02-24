import type { ApiEnvelope, Todo } from '../types'

const API_BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  let body: ApiEnvelope<T> | undefined
  try {
    body = (await response.json()) as ApiEnvelope<T>
  } catch {
    throw new Error('서버 응답을 해석할 수 없습니다.')
  }

  if (!response.ok || body.status === 'error' || body.data == null) {
    throw new Error(body.error?.message ?? '요청 처리에 실패했습니다.')
  }

  return body.data
}

export async function fetchTodos(): Promise<Todo[]> {
  const data = await request<{ items: Todo[] }>('/todos')
  return data.items
}

export async function createTodo(title: string): Promise<Todo> {
  const data = await request<{ item: Todo }>('/todos', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
  return data.item
}

export async function updateTodo(todoId: number, payload: { title?: string; is_completed?: boolean }): Promise<Todo> {
  const data = await request<{ item: Todo }>(`/todos/${todoId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
  return data.item
}

export async function deleteTodo(todoId: number): Promise<number> {
  const data = await request<{ deleted_id: number }>(`/todos/${todoId}`, {
    method: 'DELETE',
  })
  return data.deleted_id
}
